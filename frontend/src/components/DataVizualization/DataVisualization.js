import React, { useState, useEffect } from 'react';
import {
  Upload,
  FileSpreadsheet,
  BarChart3,
  LineChart,
  PieChart,
  ScatterChart,
  Database,
  Sparkles,
  Download,
  Trash2,
  Eye,
  ChevronRight,
  TrendingUp,
  Activity,
  Calendar,
  Layers,
  Settings,
  Filter,
  Search,
  X,
  Check,
  AlertCircle,
  Loader2,
  Grid3x3,
  List,
  Maximize2
} from 'lucide-react';
import './DataVisualization.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export default function DataVisualization() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [visualizations, setVisualizations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [activeTab, setActiveTab] = useState('configure'); // 'configure' or 'visualizations'
  
  const [vizConfig, setVizConfig] = useState({
    chart_type: 'scatter',
    x_column: '',
    y_column: '',
    color_column: '',
    title: '',
    library: 'plotly'
  });

  useEffect(() => {
    fetchDatasets();
    fetchVisualizations();
  }, []);

  const fetchDatasets = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/data-viz/datasets`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Tab-Session-Key': sessionStorage.getItem('tab_session_key') || ''
        }
      });
      const data = await response.json();
      if (data.success) {
        setDatasets(data.datasets);
      }
    } catch (error) {
      console.error('Failed to fetch datasets:', error);
    }
  };

  const fetchVisualizations = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/data-viz/visualizations`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Tab-Session-Key': sessionStorage.getItem('tab_session_key') || ''
        }
      });
      const data = await response.json();
      if (data.success && data.visualizations) {
        setVisualizations(data.visualizations);
      }
    } catch (error) {
      console.error('Failed to fetch visualizations:', error);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const validTypes = ['.csv', '.xlsx', '.xls'];
    const isValid = validTypes.some(type => file.name.toLowerCase().endsWith(type));
    
    if (!isValid) {
      alert('Please upload a CSV or Excel file');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const tabKey = sessionStorage.getItem('tab_session_key') || '';
      const response = await fetch(`${API_BASE_URL}/api/data-viz/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Tab-Session-Key': tabKey
        },
        body: formData
      });

      const data = await response.json();
      
      if (data.success) {
        fetchDatasets();
        setSelectedDataset(data.dataset);
        setActiveTab('configure');
      } else {
        alert(data.error || 'Failed to upload file');
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload file');
    } finally {
      setLoading(false);
    }
  };

  const handleDatasetSelect = async (dataset) => {
    setSelectedDataset(dataset);
    setVizConfig({
      ...vizConfig,
      x_column: dataset.column_names[0] || '',
      y_column: dataset.column_names[1] || '',
      title: `${dataset.filename} Visualization`
    });
    setActiveTab('configure');

    setLoading(true);
    try {
      const tabKey = sessionStorage.getItem('tab_session_key') || '';
      const response = await fetch(`${API_BASE_URL}/api/data-viz/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Tab-Session-Key': tabKey
        },
        body: JSON.stringify({ dataset_id: dataset.dataset_id })
      });

      const data = await response.json();
      if (data.success) {
        setAnalysis(data.analysis);
      }
    } catch (error) {
      console.error('Analysis error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateVisualization = async () => {
    if (!selectedDataset) {
      alert('Please select a dataset first');
      return;
    }

    if (!vizConfig.x_column) {
      alert('Please select at least an X column');
      return;
    }

    setLoading(true);

    try {
      const tabKey = sessionStorage.getItem('tab_session_key') || '';
      const response = await fetch(`${API_BASE_URL}/api/data-viz/visualize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Tab-Session-Key': tabKey
        },
        body: JSON.stringify({
          dataset_id: selectedDataset.dataset_id,
          config: vizConfig
        })
      });

      const data = await response.json();
      
      if (data.success) {
        const newViz = {
          viz_id: data.viz_id,
          chart_type: data.chart_type || vizConfig.chart_type,
          library: data.library,
          interactive: data.interactive,
          format: data.format
        };
        setVisualizations([newViz, ...visualizations]);
        setActiveTab('visualizations');
      } else {
        alert(data.error || 'Failed to generate visualization');
      }
    } catch (error) {
      console.error('Visualization error:', error);
      alert('Failed to generate visualization');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadVisualization = async (vizId, format) => {
    const url = `${API_BASE_URL}/api/data-viz/download/${vizId}?format=${format}`;
    window.open(url, '_blank');
  };

  const filteredDatasets = datasets.filter(dataset =>
    dataset.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getChartIcon = (type) => {
    const icons = {
      scatter: <ScatterChart className="chart-icon" />,
      line: <LineChart className="chart-icon" />,
      bar: <BarChart3 className="chart-icon" />,
      pie: <PieChart className="chart-icon" />,
      histogram: <Activity className="chart-icon" />,
      box: <Layers className="chart-icon" />,
      heatmap: <Grid3x3 className="chart-icon" />
    };
    return icons[type] || <BarChart3 className="chart-icon" />;
  };

  return (
    <div className="powerbi-container">
      {/* Top Navigation Bar */}
      <div className="powerbi-navbar">
        <div className="navbar-brand">
          <BarChart3 className="brand-icon" />
          <h1>Analytics Studio</h1>
        </div>
        
        <div className="navbar-actions">
          <input
            type="file"
            id="file-upload-input"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
            disabled={loading}
          />
          <label htmlFor="file-upload-input" className="btn-primary">
            <Upload size={18} />
            <span>Import Data</span>
          </label>
        </div>
      </div>

      <div className="powerbi-workspace">
        {/* Left Sidebar - Data Sources */}
        <div className="powerbi-sidebar">
          <div className="sidebar-header">
            <Database size={20} />
            <h2>Data Sources</h2>
          </div>

          {/* Search Bar */}
          <div className="sidebar-search">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search datasets..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <X 
                size={16} 
                className="search-clear" 
                onClick={() => setSearchTerm('')}
              />
            )}
          </div>

          {/* Datasets List */}
          <div className="sidebar-content">
            {filteredDatasets.length === 0 ? (
              <div className="empty-state-sidebar">
                <FileSpreadsheet size={40} />
                <p>No datasets found</p>
                <small>Upload a CSV or Excel file to get started</small>
              </div>
            ) : (
              <div className="datasets-list-modern">
                {filteredDatasets.map((dataset) => (
                  <div
                    key={dataset.dataset_id}
                    className={`dataset-item ${selectedDataset?.dataset_id === dataset.dataset_id ? 'active' : ''}`}
                    onClick={() => handleDatasetSelect(dataset)}
                  >
                    <div className="dataset-item-icon">
                      <FileSpreadsheet size={20} />
                    </div>
                    <div className="dataset-item-content">
                      <div className="dataset-item-title">{dataset.filename}</div>
                      <div className="dataset-item-meta">
                        <span>{dataset.rows} rows</span>
                        <span>•</span>
                        <span>{dataset.columns} cols</span>
                      </div>
                      <div className="dataset-item-date">
                        <Calendar size={12} />
                        {new Date(dataset.uploaded_at).toLocaleDateString()}
                      </div>
                    </div>
                    <ChevronRight size={16} className="dataset-item-arrow" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="powerbi-main">
          {selectedDataset ? (
            <>
              {/* Tab Navigation */}
              <div className="content-tabs">
                <button
                  className={`tab-button ${activeTab === 'configure' ? 'active' : ''}`}
                  onClick={() => setActiveTab('configure')}
                >
                  <Settings size={18} />
                  Configure
                </button>
                <button
                  className={`tab-button ${activeTab === 'visualizations' ? 'active' : ''}`}
                  onClick={() => setActiveTab('visualizations')}
                >
                  <BarChart3 size={18} />
                  Visualizations
                  {visualizations.length > 0 && (
                    <span className="badge">{visualizations.length}</span>
                  )}
                </button>
              </div>

              {/* Configure Tab */}
              {activeTab === 'configure' && (
                <div className="content-body">
                  {/* Data Preview Card */}
                  <div className="powerbi-card">
                    <div className="card-header">
                      <div className="card-title">
                        <Eye size={20} />
                        <h3>Data Preview</h3>
                      </div>
                      <div className="card-subtitle">
                        {selectedDataset.filename}
                      </div>
                    </div>
                    <div className="card-content">
                      <div className="table-wrapper">
                        <table className="modern-table">
                          <thead>
                            <tr>
                              {selectedDataset.column_names.map((col) => (
                                <th key={col}>{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {selectedDataset.preview.slice(0, 5).map((row, idx) => (
                              <tr key={idx}>
                                {selectedDataset.column_names.map((col) => (
                                  <td key={col}>{row[col]}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  {/* Analysis Card */}
                  {analysis && (
                    <div className="powerbi-card">
                      <div className="card-header">
                        <div className="card-title">
                          <TrendingUp size={20} />
                          <h3>Data Insights</h3>
                        </div>
                      </div>
                      <div className="card-content">
                        <div className="insights-grid">
                          {analysis.numeric_columns && analysis.numeric_columns.length > 0 && (
                            <div className="insight-group">
                              <div className="insight-label">Numeric Columns</div>
                              <div className="insight-tags">
                                {analysis.numeric_columns.map((col) => (
                                  <span key={col} className="insight-tag numeric">
                                    {col}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {analysis.categorical_columns && analysis.categorical_columns.length > 0 && (
                            <div className="insight-group">
                              <div className="insight-label">Categorical Columns</div>
                              <div className="insight-tags">
                                {analysis.categorical_columns.map((col) => (
                                  <span key={col} className="insight-tag categorical">
                                    {col}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Configuration Card */}
                  <div className="powerbi-card">
                    <div className="card-header">
                      <div className="card-title">
                        <Sparkles size={20} />
                        <h3>Create Visualization</h3>
                      </div>
                    </div>
                    <div className="card-content">
                      <div className="config-grid">
                        {/* Chart Type */}
                        <div className="config-group full-width">
                          <label className="config-label">Chart Type</label>
                          <div className="chart-type-grid">
                            {[
                              { value: 'scatter', label: 'Scatter', icon: <ScatterChart size={20} /> },
                              { value: 'line', label: 'Line', icon: <LineChart size={20} /> },
                              { value: 'bar', label: 'Bar', icon: <BarChart3 size={20} /> },
                              { value: 'pie', label: 'Pie', icon: <PieChart size={20} /> },
                              { value: 'histogram', label: 'Histogram', icon: <Activity size={20} /> },
                              { value: 'box', label: 'Box', icon: <Layers size={20} /> },
                              { value: 'heatmap', label: 'Heatmap', icon: <Grid3x3 size={20} /> }
                            ].map((chart) => (
                              <button
                                key={chart.value}
                                className={`chart-type-button ${vizConfig.chart_type === chart.value ? 'active' : ''}`}
                                onClick={() => setVizConfig({ ...vizConfig, chart_type: chart.value })}
                              >
                                {chart.icon}
                                <span>{chart.label}</span>
                                {vizConfig.chart_type === chart.value && (
                                  <Check size={16} className="check-icon" />
                                )}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Library Selection */}
                        <div className="config-group">
                          <label className="config-label">Library</label>
                          <select
                            className="modern-select"
                            value={vizConfig.library}
                            onChange={(e) => setVizConfig({ ...vizConfig, library: e.target.value })}
                          >
                            <option value="plotly">Plotly (Interactive)</option>
                            <option value="seaborn">Seaborn (Static)</option>
                            <option value="matplotlib">Matplotlib (Static)</option>
                          </select>
                        </div>

                        {/* X Column */}
                        <div className="config-group">
                          <label className="config-label">X Axis</label>
                          <select
                            className="modern-select"
                            value={vizConfig.x_column}
                            onChange={(e) => setVizConfig({ ...vizConfig, x_column: e.target.value })}
                          >
                            <option value="">Select column...</option>
                            {selectedDataset.column_names.map((col) => (
                              <option key={col} value={col}>{col}</option>
                            ))}
                          </select>
                        </div>

                        {/* Y Column */}
                        {vizConfig.chart_type !== 'histogram' && vizConfig.chart_type !== 'pie' && (
                          <div className="config-group">
                            <label className="config-label">Y Axis</label>
                            <select
                              className="modern-select"
                              value={vizConfig.y_column}
                              onChange={(e) => setVizConfig({ ...vizConfig, y_column: e.target.value })}
                            >
                              <option value="">Select column...</option>
                              {selectedDataset.column_names.map((col) => (
                                <option key={col} value={col}>{col}</option>
                              ))}
                            </select>
                          </div>
                        )}

                        {/* Color Column */}
                        <div className="config-group">
                          <label className="config-label">Color By (Optional)</label>
                          <select
                            className="modern-select"
                            value={vizConfig.color_column}
                            onChange={(e) => setVizConfig({ ...vizConfig, color_column: e.target.value })}
                          >
                            <option value="">None</option>
                            {selectedDataset.column_names.map((col) => (
                              <option key={col} value={col}>{col}</option>
                            ))}
                          </select>
                        </div>

                        {/* Title */}
                        <div className="config-group full-width">
                          <label className="config-label">Chart Title</label>
                          <input
                            type="text"
                            className="modern-input"
                            value={vizConfig.title}
                            onChange={(e) => setVizConfig({ ...vizConfig, title: e.target.value })}
                            placeholder="Enter chart title..."
                          />
                        </div>
                      </div>

                      {/* Generate Button */}
                      <button
                        className="btn-generate"
                        onClick={handleGenerateVisualization}
                        disabled={loading || !vizConfig.x_column}
                      >
                        {loading ? (
                          <>
                            <Loader2 size={18} className="spinning" />
                            <span>Generating...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles size={18} />
                            <span>Generate Visualization</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Visualizations Tab */}
              {activeTab === 'visualizations' && (
                <div className="content-body">
                  {visualizations.length === 0 ? (
                    <div className="empty-state-main">
                      <BarChart3 size={64} />
                      <h3>No Visualizations Yet</h3>
                      <p>Create your first visualization to see it here</p>
                      <button
                        className="btn-primary"
                        onClick={() => setActiveTab('configure')}
                      >
                        <Sparkles size={18} />
                        Create Visualization
                      </button>
                    </div>
                  ) : (
                    <>
                      {/* View Mode Toggle */}
                      <div className="view-controls">
                        <div className="view-toggle">
                          <button
                            className={viewMode === 'grid' ? 'active' : ''}
                            onClick={() => setViewMode('grid')}
                            title="Grid View"
                          >
                            <Grid3x3 size={18} />
                          </button>
                          <button
                            className={viewMode === 'list' ? 'active' : ''}
                            onClick={() => setViewMode('list')}
                            title="List View"
                          >
                            <List size={18} />
                          </button>
                        </div>
                      </div>

                      {/* Visualizations Grid */}
                      <div className={`viz-grid ${viewMode}`}>
                        {visualizations.map((viz, idx) => (
                          <div key={idx} className="viz-card">
                            <div className="viz-card-preview">
                              {viz.interactive ? (
                                <iframe
                                  src={`${API_BASE_URL}/api/data-viz/download/${viz.viz_id}?format=html`}
                                  title={`Visualization ${idx + 1}`}
                                />
                              ) : (
                                <img
                                  src={`${API_BASE_URL}/api/data-viz/download/${viz.viz_id}?format=png`}
                                  alt={`Visualization ${idx + 1}`}
                                />
                              )}
                            </div>
                            <div className="viz-card-footer">
                              <div className="viz-card-info">
                                <div className="viz-card-type">
                                  {getChartIcon(viz.chart_type)}
                                  <span>{viz.chart_type}</span>
                                </div>
                                <div className="viz-card-library">
                                  {viz.library}
                                </div>
                              </div>
                              <div className="viz-card-actions">
                                <button
                                  className="btn-icon"
                                  onClick={() => handleDownloadVisualization(viz.viz_id, viz.interactive ? 'html' : 'png')}
                                  title="Download"
                                >
                                  <Download size={18} />
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="empty-state-main">
              <Database size={64} />
              <h3>Welcome to Analytics Studio</h3>
              <p>Select a dataset from the sidebar or upload a new one to get started</p>
              <label htmlFor="file-upload-input" className="btn-primary">
                <Upload size={18} />
                Import Data
              </label>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}