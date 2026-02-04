import cgi
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import base64
from bson import ObjectId
import re
import traceback

# MongoDB imports
from database import datasets, dataset_files, visualizations

# Set Seaborn style
sns.set_theme(style="whitegrid")


class DataVizController:
    """Handle data visualization operations with MongoDB storage"""
    
    @staticmethod
    def upload_file(file_data, filename, user_id):
        """
        Upload and process CSV/Excel file
        Stores in MongoDB instead of filesystem
        """
        try:
            # Load into pandas based on file type
            if filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_data))
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(file_data))
            else:
                return {
                    "error": "Unsupported file format. Please upload CSV or Excel files."
                }
            
            # Convert DataFrame to JSON (for storage)
            # Store as records format for easy querying
            data_records = df.to_dict('records')
            
            # Prepare metadata
            metadata = {
                "user_id": user_id,
                "filename": filename,
                "uploaded_at": datetime.utcnow(),
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "column_types": df.dtypes.astype(str).to_dict(),
                "size_bytes": len(file_data),
                "preview": df.head(10).to_dict('records')
            }
            
            # Check size - if dataset is small (<1MB), store directly
            # If large, chunk it
            if len(file_data) < 1_000_000:  # 1MB
                # Store small dataset directly in metadata
                metadata["data"] = data_records
                metadata["storage_type"] = "inline"
                
                # Insert into MongoDB
                result = datasets.insert_one(metadata)
                dataset_id = str(result.inserted_id)
            else:
                # Large dataset - store in chunks
                metadata["storage_type"] = "chunked"
                
                # Insert metadata first
                result = datasets.insert_one(metadata)
                dataset_id = str(result.inserted_id)
                
                # Store data in chunks (16MB chunks - MongoDB document limit)
                chunk_size = 10_000  # rows per chunk
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i:i+chunk_size]
                    chunk_data = chunk.to_dict('records')
                    
                    dataset_files.insert_one({
                        "dataset_id": dataset_id,
                        "chunk_index": i // chunk_size,
                        "data": chunk_data,
                        "created_at": datetime.utcnow()
                    })
            
            # Add dataset_id to metadata for response
            metadata["dataset_id"] = dataset_id
            metadata["_id"] = dataset_id  # For consistency
            
            # Remove data from response (too large)
            if "data" in metadata:
                del metadata["data"]
            
            # Convert datetime to string for JSON
            metadata["uploaded_at"] = metadata["uploaded_at"].isoformat()
            
            return {
                "success": True,
                "dataset": metadata
            }
            
        except Exception as e:
            print(f"Upload error: {e}")
            traceback.print_exc()
            return {
                "error": f"Failed to upload file: {str(e)}"
            }
    
    @staticmethod
    def get_datasets(user_id):
        """Get list of user's uploaded datasets from MongoDB"""
        try:
            # Query MongoDB for user's datasets
            cursor = datasets.find(
                {"user_id": user_id},
                {
                    "_id": 1,
                    "filename": 1,
                    "uploaded_at": 1,
                    "rows": 1,
                    "columns": 1,
                    "column_names": 1,
                    "column_types": 1,
                    "size_bytes": 1,
                    "preview": 1
                }
            ).sort("uploaded_at", -1)
            
            # Convert to list and format
            dataset_list = []
            for doc in cursor:
                dataset_info = {
                    "dataset_id": str(doc["_id"]),
                    "filename": doc["filename"],
                    "uploaded_at": doc["uploaded_at"].isoformat() if isinstance(doc["uploaded_at"], datetime) else doc["uploaded_at"],
                    "rows": doc["rows"],
                    "columns": doc["columns"],
                    "column_names": doc.get("column_names", []),
                    "column_types": doc.get("column_types", {}),
                    "size_bytes": doc.get("size_bytes", 0),
                    "preview": doc.get("preview", [])
                }
                dataset_list.append(dataset_info)
            
            return {
                "success": True,
                "datasets": dataset_list
            }
            
        except Exception as e:
            print(f"Get datasets error: {e}")
            traceback.print_exc()
            return {
                "error": f"Failed to get datasets: {str(e)}"
            }
    
    @staticmethod
    def _coerce_numeric_columns(df):
        """Attempt pd.to_numeric on every object-dtype column.

        MongoDB / PyMongo can return a column as a mix of str and int/float
        inside a single object-dtype Series (e.g. some rows come back as
        the string "25", others as the int 18).  pd.to_numeric converts the
        values but the Series dtype may remain object unless we explicitly
        cast.  We therefore call .astype(float) after a successful
        conversion so that pandas actually uses a numeric dtype.

        This prevents:
            - 'agg function failed [how->mean,dtype->object]'
            - "'value' must be an instance of str or bytes, not a float"
            - inverted / lexicographically-sorted axes
        """
        for col in df.select_dtypes(include=["object"]).columns:
            converted = pd.to_numeric(df[col], errors="coerce")
            # Keep only when no *new* NaNs were introduced (i.e. every
            # non-null original value was genuinely numeric)
            if converted.notna().sum() == df[col].notna().sum():
                # Force the dtype to float64 so pandas stops treating it
                # as object even when the Series already contained ints
                df[col] = converted.astype(float)
        return df

    @staticmethod
    def _load_dataset_dataframe(dataset_id):
        """Load dataset from MongoDB into pandas DataFrame.

        After constructing the DataFrame we call _coerce_numeric_columns()
        to restore numeric dtypes that were lost during the JSON round-trip
        through MongoDB.
        """
        try:
            # Get metadata
            dataset_doc = datasets.find_one({"_id": ObjectId(dataset_id)})
            if not dataset_doc:
                return None, "Dataset not found"

            storage_type = dataset_doc.get("storage_type", "inline")

            if storage_type == "inline":
                data_records = dataset_doc.get("data", [])
                df = pd.DataFrame(data_records)
            else:
                chunks_cursor = dataset_files.find(
                    {"dataset_id": dataset_id}
                ).sort("chunk_index", 1)

                all_data = []
                for chunk_doc in chunks_cursor:
                    all_data.extend(chunk_doc["data"])

                df = pd.DataFrame(all_data)

            # Restore numeric dtypes lost in JSON serialisation
            df = DataVizController._coerce_numeric_columns(df)

            return df, None

        except Exception as e:
            print(f"Load dataset error: {e}")
            traceback.print_exc()
            return None, str(e)
    
    @staticmethod
    def analyze_data(dataset_id):
        """Analyze dataset from MongoDB"""
        try:
            # Load DataFrame
            df, error = DataVizController._load_dataset_dataframe(dataset_id)
            if error:
                return {"error": error}
            
            # Separate numeric and categorical columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            analysis = {
                "summary_stats": df.describe().to_dict() if numeric_cols else {},
                "missing_values": df.isnull().sum().to_dict(),
                "numeric_columns": numeric_cols,
                "categorical_columns": categorical_cols,
                "data_types": df.dtypes.astype(str).to_dict()
            }
            
            # Correlation matrix for numeric columns
            if len(numeric_cols) > 1:
                analysis["correlation_matrix"] = df[numeric_cols].corr().to_dict()
            
            # Value counts for categorical columns (top 10)
            if categorical_cols:
                analysis["categorical_distributions"] = {}
                for col in categorical_cols[:5]:
                    value_counts = df[col].value_counts().head(10).to_dict()
                    analysis["categorical_distributions"][col] = value_counts
            
            return {
                "success": True,
                "analysis": analysis
            }
            
        except Exception as e:
            print(f"Analyze error: {e}")
            traceback.print_exc()
            return {
                "error": f"Failed to analyze data: {str(e)}"
            }
    
    
    @staticmethod
    def _generate_plotly_mongo(df, chart_type, x_col, y_col, color_col, title, dataset_id, viz_config=None, user_id=None):
        """Generate Plotly visualization and store HTML in MongoDB"""
        try:
            # Handle empty color column (convert to None)
            # This is CRITICAL - Plotly crashes on empty strings
            if not color_col or (isinstance(color_col, str) and color_col.strip() == ''):
                color_col = None
            
            # Generate plotly figure based on chart type
            if chart_type == "scatter":
                fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title)
            elif chart_type == "line":
                fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title)
            elif chart_type == "bar":
                fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title)
    
            elif chart_type == "histogram":
                fig = px.histogram(df, x=x_col, color=color_col, title=title)
            elif chart_type == "box":
                fig = px.box(df, x=x_col, y=y_col, color=color_col, title=title)
            elif chart_type == "violin":
                fig = px.violin(df, x=x_col, y=y_col, color=color_col, title=title)
            elif chart_type == "heatmap":
                # Heatmap doesn't use x_col, y_col, or color
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) < 2:
                    return {"error": "Heatmap requires at least 2 numeric columns"}
                corr_matrix = df[numeric_cols].corr()
                fig = px.imshow(corr_matrix, text_auto=True, title=title, 
                            labels=dict(color="Correlation"))
            elif chart_type == "pie":
                # Pie chart only uses x_col
                value_counts = df[x_col].value_counts()
                fig = px.pie(values=value_counts.values, names=value_counts.index, title=title)
            else:
                return {"error": f"Unsupported chart type: {chart_type}"}
            
            # Improve layout
            fig.update_layout(
                template="plotly_white",
                hovermode='closest',
                showlegend=True if color_col else False,
                font=dict(size=12),
                title_font_size=16
            )
            
            # Convert to HTML string with responsive config
            html_string = fig.to_html(
                include_plotlyjs='cdn',
                config={'responsive': True, 'displayModeBar': True}
            )
            
            # Store in MongoDB
            viz_doc = {
                "dataset_id": dataset_id,
                "user_id": user_id,
                "chart_type": chart_type,
                "library": "plotly",
                "format": "html",
                "html_content": html_string,
                "config": viz_config or {},
                "created_at": datetime.utcnow()
            }
            
            result = visualizations.insert_one(viz_doc)
            viz_id = str(result.inserted_id)
            
            return {
                "success": True,
                "viz_id": viz_id,
                "library": "plotly",
                "interactive": True,
                "format": "html"
            }
            
        except Exception as e:
            print(f"Plotly error: {e}")
            traceback.print_exc()
            return {"error": f"Plotly error: {str(e)}"}
    
    @staticmethod
    def _generate_static_mongo(df, chart_type, x_col, y_col, color_col, title, dataset_id, library, viz_config=None, user_id=None):
        """Generate static visualization and store base64 image in MongoDB"""
        try:
            # Handle empty color column
            if not color_col or (isinstance(color_col, str) and color_col.strip() == ''):
                color_col = None

            fig, ax = plt.subplots(figsize=(12, 6))

            # Detect whether x_col is categorical (object / string dtype)
            x_is_categorical = df[x_col].dtype == object

            # ── seaborn ─────────────────────────────────────────────────
            if library == "seaborn":
                if chart_type == "scatter":
                    sns.scatterplot(data=df, x=x_col, y=y_col, hue=color_col, ax=ax)
                elif chart_type == "line":
                    sns.lineplot(data=df, x=x_col, y=y_col, hue=color_col, ax=ax)
                elif chart_type == "bar":
                    sns.barplot(data=df, x=x_col, y=y_col, hue=color_col, ax=ax)
                    # Ensure y-axis starts at 0 and increases upward
                    ax.set_ylim(bottom=0)
                elif chart_type == "histogram":
                    sns.histplot(data=df, x=x_col, hue=color_col, kde=True, ax=ax)
                elif chart_type == "box":
                    sns.boxplot(data=df, x=x_col, y=y_col, hue=color_col, ax=ax)
                elif chart_type == "violin":
                    sns.violinplot(data=df, x=x_col, y=y_col, hue=color_col, ax=ax)

            # ── matplotlib ──────────────────────────────────────────────
            else:
                if chart_type == "scatter":
                    if color_col:
                        for category in df[color_col].unique():
                            mask = df[color_col] == category
                            ax.scatter(df.loc[mask, x_col], df.loc[mask, y_col], label=str(category))
                        ax.legend()
                    else:
                        ax.scatter(df[x_col], df[y_col])

                elif chart_type == "line":
                    if x_is_categorical:
                        # Plot by positional index so matplotlib doesn't
                        # try to interpret string names as numbers
                        ax.plot(range(len(df)), df[y_col].values, marker='o', markersize=3)
                        ax.set_xticks(range(len(df)))
                        ax.set_xticklabels(df[x_col].values, rotation=45, ha='right', fontsize=7)
                    else:
                        ax.plot(df[x_col], df[y_col])

                elif chart_type == "bar":
                    if x_is_categorical:
                        # If every x value is unique (or nearly so) skip
                        # groupby — just plot directly.  Otherwise group &
                        # take the mean.
                        if df[x_col].nunique() == len(df):
                            ax.bar(range(len(df)), df[y_col].values)
                            ax.set_xticks(range(len(df)))
                            ax.set_xticklabels(df[x_col].values, rotation=45, ha='right', fontsize=7)
                        else:
                            grouped = df.groupby(x_col)[y_col].mean()
                            ax.bar(range(len(grouped)), grouped.values)
                            ax.set_xticks(range(len(grouped)))
                            ax.set_xticklabels(grouped.index, rotation=45, ha='right', fontsize=7)
                    else:
                        grouped = df.groupby(x_col)[y_col].mean()
                        ax.bar(grouped.index, grouped.values)
                    # Ensure y-axis starts at 0 and increases upward
                    ax.set_ylim(bottom=0)

                elif chart_type == "histogram":
                    ax.hist(df[x_col], bins=30, edgecolor='black')

            # ── shared labels & label rotation ──────────────────────────
            ax.set_title(title)
            ax.set_xlabel(x_col)
            if y_col:
                ax.set_ylabel(y_col)

            # Rotate x-labels for seaborn / scatter / histogram too when
            # the axis is categorical or has many tick labels
            if x_is_categorical or len(ax.get_xticklabels()) > 10:
                ax.tick_params(axis='x', rotation=45)
                for lbl in ax.get_xticklabels():
                    lbl.set_fontsize(7)
                    lbl.set_ha('right')

            fig.tight_layout()
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            
            # Store in MongoDB
            viz_doc = {
                "dataset_id": dataset_id,
                "user_id": user_id,
                "chart_type": chart_type,
                "library": library,
                "format": "png",
                "image_base64": image_base64,
                "config": viz_config or {},
                "created_at": datetime.utcnow()
            }
            
            result = visualizations.insert_one(viz_doc)
            viz_id = str(result.inserted_id)
            
            return {
                "success": True,
                "viz_id": viz_id,
                "library": library,
                "interactive": False,
                "format": "png"
            }
            
        except Exception as e:
            plt.close()
            print(f"{library} error: {e}")
            traceback.print_exc()
            return {"error": f"{library} error: {str(e)}"}
    
    @staticmethod
    def get_visualization(viz_id):
        """Retrieve visualization from MongoDB"""
        try:
            viz_doc = visualizations.find_one({"_id": ObjectId(viz_id)})
            if not viz_doc:
                return None, None, "Visualization not found"
            
            format_type = viz_doc.get("format", "png")
            
            if format_type == "html":
                # Return HTML
                content = viz_doc["html_content"].encode('utf-8')
                content_type = "text/html"
            else:
                # Return PNG (decode base64)
                content = base64.b64decode(viz_doc["image_base64"])
                content_type = "image/png"
            
            return content, content_type, None
            
        except Exception as e:
            print(f"Get visualization error: {e}")
            return None, None, str(e)
    @staticmethod
    def generate_visualization(dataset_id, viz_config, user_id=None):
        """Generate visualization and store in MongoDB (tagged with user_id)"""
        try:
            # Load DataFrame
            df, error = DataVizController._load_dataset_dataframe(dataset_id)
            if error:
                return {"error": error}
            
            chart_type = viz_config.get("chart_type", "scatter")
            library = viz_config.get("library", "plotly")
            x_col = viz_config.get("x_column")
            y_col = viz_config.get("y_column")
            color_col = viz_config.get("color_column")
            # Clean empty strings to None (CRITICAL for Plotly)
            if not color_col or (isinstance(color_col, str) and color_col.strip() == ''):
                color_col = None
            title = viz_config.get("title", f"{chart_type.title()} Chart")
            
            # Generate visualization based on library
            if library == "plotly":
                result = DataVizController._generate_plotly_mongo(
                    df, chart_type, x_col, y_col, color_col, title, dataset_id, viz_config, user_id
                )
            elif library == "seaborn":
                result = DataVizController._generate_static_mongo(
                    df, chart_type, x_col, y_col, color_col, title, dataset_id, "seaborn", viz_config, user_id
                )
            else:  # matplotlib
                result = DataVizController._generate_static_mongo(
                    df, chart_type, x_col, y_col, color_col, title, dataset_id, "matplotlib", viz_config, user_id
                )
            
            # Return the result
            return result
            
        except Exception as e:
            print(f"Generate visualization error: {e}")
            traceback.print_exc()
            return {"error": f"Failed to generate visualization: {str(e)}"}

    @staticmethod
    def get_user_visualizations(user_id):
        """Retrieve all visualizations belonging to a user, newest first."""
        try:
            cursor = visualizations.find(
                {"user_id": user_id},
                {
                    "_id": 1,
                    "dataset_id": 1,
                    "chart_type": 1,
                    "library": 1,
                    "format": 1,
                    "created_at": 1,
                    "config": 1
                }
            ).sort("created_at", -1)

            viz_list = []
            for doc in cursor:
                viz_list.append({
                    "viz_id": str(doc["_id"]),
                    "dataset_id": doc.get("dataset_id"),
                    "chart_type": doc.get("chart_type"),
                    "library": doc.get("library"),
                    "format": doc.get("format"),
                    "interactive": doc.get("format") == "html",
                    "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc.get("created_at"),
                    "config": doc.get("config", {})
                })

            return {"success": True, "visualizations": viz_list}

        except Exception as e:
            print(f"Get user visualizations error: {e}")
            traceback.print_exc()
            return {"error": f"Failed to fetch visualizations: {str(e)}"}

# Route handlers
"""
FIXED handle_upload function for data_viz_controller.py
Replace the 'pass' statement at line 2145-2149 with this implementation
"""

def handle_upload(request_handler, body_bytes, user_id):
    """Handle multipart file upload using manual parsing (avoids UTF-8 issues)"""
    try:
        # Parse multipart form data manually to avoid UTF-8 decoding issues
        content_type = request_handler.headers.get('Content-Type', '')
        
        if not content_type.startswith('multipart/form-data'):
            return error_response("Content-Type must be multipart/form-data", 400)
        
        # Extract boundary from Content-Type header
        boundary = None
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                boundary = part.split('=', 1)[1].strip('"')
                break
        
        if not boundary:
            return error_response("No boundary found in Content-Type", 400)
        
        # Convert boundary to bytes for searching
        boundary_bytes = ('--' + boundary).encode('utf-8')
        
        # Split the body by boundary
        parts = body_bytes.split(boundary_bytes)
        
        file_data = None
        filename = None
        
        # Parse each part
        for part in parts:
            if not part or part == b'--\r\n' or part == b'--':
                continue
            
            try:
                header_end = part.find(b'\r\n\r\n')
                if header_end == -1:
                    continue
                
                headers = part[:header_end].decode('utf-8', errors='ignore')
                content = part[header_end + 4:]
                
                if content.endswith(b'\r\n'):
                    content = content[:-2]
                
                if 'filename=' in headers:
                    for line in headers.split('\r\n'):
                        if line.startswith('Content-Disposition:'):
                            parts_list = line.split(';')
                            for p in parts_list:
                                p = p.strip()
                                if p.startswith('filename='):
                                    filename = p.split('=', 1)[1].strip('"')
                                    break
                    file_data = content
                    break
            except Exception as parse_error:
                print(f"Error parsing part: {parse_error}")
                continue
        
        if not file_data or not filename:
            return error_response("No file provided or filename missing", 400)
        
        print(f"✓ Received file: {filename}, size: {len(file_data)} bytes")
        
        result = DataVizController.upload_file(file_data, filename, user_id)
        
        if result.get("error"):
            return error_response(result["error"], 400)
        
        return success_response(result, 201)
        
    except Exception as e:
        print(f"Upload handler error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(f"Upload failed: {str(e)}", 500)


def handle_get_datasets(user_id):
    """Get user's datasets"""
    result = DataVizController.get_datasets(user_id)
    if result.get("error"):
        return error_response(result["error"], 400)
    return success_response(result)


def handle_get_visualizations(user_id):
    """Get all visualizations for the authenticated user"""
    if not user_id:
        return error_response("Unauthorized", 401)
    result = DataVizController.get_user_visualizations(user_id)
    if result.get("error"):
        return error_response(result["error"], 400)
    return success_response(result)

def handle_analyze(body_str, user_id):
    """Analyze dataset"""
    try:
        data = json.loads(body_str)
        dataset_id = data.get("dataset_id")
        
        if not dataset_id:
            return error_response("dataset_id required", 400)
        
        # Verify dataset belongs to user
        from bson import ObjectId
        from database import datasets as datasets_collection
        
        dataset = datasets_collection.find_one({"_id": ObjectId(dataset_id)})
        if not dataset:
            return error_response("Dataset not found", 404)
        if dataset.get("user_id") != user_id:
            return error_response("Unauthorized access to dataset", 403)
        
        result = DataVizController.analyze_data(dataset_id)
        if result.get("error"):
            return error_response(result["error"], 400)
        return success_response(result)
        
    except Exception as e:
        print(f"Analyze error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)
    


def handle_visualize(body_str, user_id):
    """Generate visualization"""
    try:
        data = json.loads(body_str)
        dataset_id = data.get("dataset_id")
        viz_config = data.get("config", {})
        
        if not dataset_id:
            return error_response("dataset_id required", 400)
        
        # Verify dataset belongs to user
        from bson import ObjectId
        from database import datasets as datasets_collection
        
        dataset = datasets_collection.find_one({"_id": ObjectId(dataset_id)})
        if not dataset:
            return error_response("Dataset not found", 404)
        if dataset.get("user_id") != user_id:
            return error_response("Unauthorized access to dataset", 403)
        
        result = DataVizController.generate_visualization(dataset_id, viz_config, user_id)
        if result.get("error"):
            return error_response(result["error"], 400)
        return success_response(result, 201)
        
    except Exception as e:
        print(f"Visualize error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)

def handle_download(viz_id, format='png'):
    """Download visualization.
    
    Returns (content, content_type, filename, inline).
    `inline` is True for HTML so that <iframe> can render it without
    the browser forcing a file download.
    """
    try:
        content, content_type, error = DataVizController.get_visualization(viz_id)
        if error:
            return None, None, None, False
        # HTML must be served inline for iframe rendering; everything
        # else is an attachment download.
        inline = (content_type == "text/html")
        return content, content_type, f"viz_{viz_id}.{format}", inline
        
    except Exception as e:
        print(f"Download error: {e}")
        return None, None, None, False


def success_response(data, status=200):
    """Helper to create success response"""
    return {
        "status": status,
        "headers": [("Content-Type", "application/json")],
        "body": json.dumps(data)
    }


def error_response(message, status=400):
    """Helper to create error response"""
    return {
        "status": status,
        "headers": [("Content-Type", "application/json")],
        "body": json.dumps({"error": message})
    }