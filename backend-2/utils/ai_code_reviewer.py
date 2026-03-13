"""
AI Code Reviewer using Azure OpenAI GPT-5.2-chat
Provides intelligent code analysis, architecture feedback, and best practices
"""
import json
from typing import List, Dict, Any
from models.code_review import AIReviewInsight, SecurityFinding
from utils.azure_ai_utils import chat_completion


class AICodeReviewer:
    """Uses GPT-5.2 to provide intelligent code review insights"""
    
    def __init__(self):
        self.model_name = "GPT-4o"
    
    async def analyze_pr(
        self,
        pr_data: Dict[str, Any],
        changed_files: List[Dict[str, Any]],
        security_findings: List[SecurityFinding],
        quality_metrics: Dict[str, Any]
    ) -> AIReviewInsight:
        """
        Perform comprehensive AI analysis of a pull request
        
        Args:
            pr_data: PR metadata (title, description, author, etc.)
            changed_files: List of changed files with diffs
            security_findings: Security issues found by scanners
            quality_metrics: Code quality metrics
        
        Returns:
            AIReviewInsight with comprehensive analysis
        """
        # Build context for AI
        context = self._build_review_context(pr_data, changed_files, security_findings, quality_metrics)
        
        # Create system prompt for code review
        system_prompt = """You are an expert code reviewer with deep knowledge of software architecture, 
security best practices, and clean code principles. Your role is to provide constructive, actionable 
feedback on pull requests.

Analyze the code changes and provide:
1. A concise summary of the changes
2. Key strengths in the implementation
3. Areas for improvement or potential issues
4. Architecture and design feedback
5. Specific best practice recommendations

Be thorough but concise. Focus on meaningful insights that will help improve code quality."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            # Call Azure OpenAI GPT-5.2
            response = chat_completion(
                messages=messages,
                max_tokens=2000,
                temperature=1.0
            )
            
            # Parse AI response
            ai_response = response['content']
            
            # Extract structured insights from AI response
            insights = self._parse_ai_response(ai_response, security_findings)
            
            return insights
        
        except Exception as e:
            print(f"[AI REVIEWER ERROR] {str(e)}")
            # Return fallback insights
            return AIReviewInsight(
                summary="AI analysis unavailable. Manual review recommended.",
                strengths=["Code changes submitted for review"],
                weaknesses=["AI analysis could not be completed"],
                architecture_feedback="Please perform manual code review.",
                best_practices=[],
                estimated_risk_level=self._calculate_risk_level(security_findings)
            )
    
    def _build_review_context(
        self,
        pr_data: Dict[str, Any],
        changed_files: List[Dict[str, Any]],
        security_findings: List[SecurityFinding],
        quality_metrics: Dict[str, Any]
    ) -> str:
        """Build comprehensive context for AI review"""
        
        context_parts = []
        
        # PR Overview
        context_parts.append(f"## Pull Request Overview")
        context_parts.append(f"**Title:** {pr_data.get('title', 'N/A')}")
        context_parts.append(f"**Author:** {pr_data.get('author', 'N/A')}")
        context_parts.append(f"**Description:** {pr_data.get('description', 'No description provided')}")
        context_parts.append("")
        
        # Changed Files Summary
        context_parts.append(f"## Changed Files ({len(changed_files)} files)")
        total_additions = sum(f.get('additions', 0) for f in changed_files)
        total_deletions = sum(f.get('deletions', 0) for f in changed_files)
        context_parts.append(f"**Total Changes:** +{total_additions} -{total_deletions}")
        context_parts.append("")
        
        # File-by-file breakdown (limit to prevent context overflow)
        max_files_detail = 10
        for i, file_info in enumerate(changed_files[:max_files_detail]):
            context_parts.append(f"### File {i+1}: {file_info['filename']}")
            context_parts.append(f"Changes: +{file_info.get('additions', 0)} -{file_info.get('deletions', 0)}")
            
            # Include patch/diff (truncated)
            patch = file_info.get('patch', '')
            if patch:
                # Limit patch size
                patch_lines = patch.split('\n')[:50]  # First 50 lines
                context_parts.append("```diff")
                context_parts.extend(patch_lines)
                if len(patch.split('\n')) > 50:
                    context_parts.append("... (truncated)")
                context_parts.append("```")
            context_parts.append("")
        
        if len(changed_files) > max_files_detail:
            context_parts.append(f"... and {len(changed_files) - max_files_detail} more files")
            context_parts.append("")
        
        # Security Findings
        if security_findings:
            context_parts.append(f"## Security Findings ({len(security_findings)} issues)")
            
            # Group by severity
            critical = [f for f in security_findings if f.severity == 'critical']
            high = [f for f in security_findings if f.severity == 'high']
            medium = [f for f in security_findings if f.severity == 'medium']
            
            if critical:
                context_parts.append(f"**Critical Issues:** {len(critical)}")
                for finding in critical[:3]:  # Show first 3
                    context_parts.append(f"- {finding.type}: {finding.message} ({finding.file_path}:{finding.line_number})")
            
            if high:
                context_parts.append(f"**High Severity:** {len(high)}")
                for finding in high[:3]:
                    context_parts.append(f"- {finding.type}: {finding.message} ({finding.file_path}:{finding.line_number})")
            
            if medium:
                context_parts.append(f"**Medium Severity:** {len(medium)}")
            
            context_parts.append("")
        
        # Quality Metrics
        context_parts.append(f"## Code Quality Metrics")
        context_parts.append(f"**Complexity Score:** {quality_metrics.get('complexity_score', 0):.1f}/10")
        context_parts.append(f"**Documentation Score:** {quality_metrics.get('documentation_score', 0):.1f}/10")
        context_parts.append(f"**Test Coverage Indicator:** {quality_metrics.get('test_coverage_indicator', 0):.1f}/10")
        context_parts.append(f"**Maintainability Score:** {quality_metrics.get('maintainability_score', 0):.1f}/10")
        
        if quality_metrics.get('issues'):
            context_parts.append("**Issues:**")
            for issue in quality_metrics['issues'][:5]:  # First 5 issues
                context_parts.append(f"- {issue}")
        
        context_parts.append("")
        context_parts.append("## Review Request")
        context_parts.append("Please provide a comprehensive code review covering:")
        context_parts.append("1. Summary of changes and their purpose")
        context_parts.append("2. Strengths in the implementation")
        context_parts.append("3. Weaknesses or areas for improvement")
        context_parts.append("4. Architecture and design feedback")
        context_parts.append("5. Best practice recommendations with specific suggestions")
        
        return "\n".join(context_parts)
    
    def _parse_ai_response(self, ai_response: str, security_findings: List[SecurityFinding]) -> AIReviewInsight:
        """Parse AI response into structured AIReviewInsight"""
        
        # Split response into sections
        lines = ai_response.split('\n')
        
        summary = ""
        strengths = []
        weaknesses = []
        architecture_feedback = ""
        best_practices = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if any(keyword in line.lower() for keyword in ['summary', 'overview', 'changes']):
                current_section = 'summary'
                continue
            elif any(keyword in line.lower() for keyword in ['strength', 'positive', 'good']):
                current_section = 'strengths'
                continue
            elif any(keyword in line.lower() for keyword in ['weakness', 'issue', 'concern', 'improvement']):
                current_section = 'weaknesses'
                continue
            elif any(keyword in line.lower() for keyword in ['architecture', 'design', 'structure']):
                current_section = 'architecture'
                continue
            elif any(keyword in line.lower() for keyword in ['best practice', 'recommendation', 'suggestion']):
                current_section = 'best_practices'
                continue
            
            # Add content to appropriate section
            if not line or line.startswith('#'):
                continue
            
            if current_section == 'summary':
                summary += line + " "
            elif current_section == 'strengths' and line.startswith(('-', '*', '•')):
                strengths.append(line.lstrip('-*• '))
            elif current_section == 'weaknesses' and line.startswith(('-', '*', '•')):
                weaknesses.append(line.lstrip('-*• '))
            elif current_section == 'architecture':
                architecture_feedback += line + " "
            elif current_section == 'best_practices' and line.startswith(('-', '*', '•')):
                # Try to split into issue/suggestion
                parts = line.lstrip('-*• ').split(':', 1)
                if len(parts) == 2:
                    best_practices.append({
                        "issue": parts[0].strip(),
                        "suggestion": parts[1].strip()
                    })
                else:
                    best_practices.append({
                        "issue": "General Recommendation",
                        "suggestion": line.lstrip('-*• ')
                    })
        
        # Fallback if parsing failed
        if not summary:
            summary = ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
        
        if not strengths:
            strengths = ["Code changes implemented as requested"]
        
        if not weaknesses:
            weaknesses = ["See detailed security findings for specific issues"]
        
        if not architecture_feedback:
            architecture_feedback = "Architecture review completed. See specific recommendations below."
        
        # Calculate risk level
        risk_level = self._calculate_risk_level(security_findings)
        
        return AIReviewInsight(
            summary=summary.strip(),
            strengths=strengths,
            weaknesses=weaknesses,
            architecture_feedback=architecture_feedback.strip(),
            best_practices=best_practices,
            estimated_risk_level=risk_level
        )
    
    def _calculate_risk_level(self, security_findings: List[SecurityFinding]) -> str:
        """Calculate overall risk level based on security findings"""
        if not security_findings:
            return "low"
        
        critical_count = sum(1 for f in security_findings if f.severity == 'critical')
        high_count = sum(1 for f in security_findings if f.severity == 'high')
        
        if critical_count > 0:
            return "critical"
        elif high_count >= 3:
            return "high"
        elif high_count > 0:
            return "medium"
        else:
            return "low"
    
    async def generate_review_summary(self, review_data: Dict[str, Any]) -> str:
        """Generate a concise summary for notifications or dashboards"""
        critical = review_data.get('critical_issues_count', 0)
        high = review_data.get('high_issues_count', 0)
        quality_score = review_data.get('quality_score', 0)
        security_score = review_data.get('security_score', 0)
        
        if critical > 0:
            return f"⚠️ {critical} critical issues found. Immediate attention required."
        elif high > 0:
            return f"🔍 {high} high-severity issues detected. Review recommended."
        elif quality_score < 7:
            return f"📊 Code quality score: {quality_score:.1f}/10. Consider improvements."
        elif security_score < 7:
            return f"🔒 Security score: {security_score:.1f}/10. Review security findings."
        else:
            return f"✅ Review completed successfully. Quality: {quality_score:.1f}/10, Security: {security_score:.1f}/10"
