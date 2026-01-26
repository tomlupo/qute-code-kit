#!/usr/bin/env python3
"""
Script to create a comprehensive Claude Code subagent workflow example
Run this script to generate the complete project structure as a zip file
"""

import os
import zipfile
import json
from pathlib import Path

def create_workflow_zip():
    """Create a zip file with complete subagent workflow example"""
    
    # Define the project structure and files
    files_to_create = {
        # Main workflow file
        "workflow.md": """# Multi-Agent Data Analysis Workflow

This workflow demonstrates how to structure subagents in Claude Code for a complete data analysis pipeline.

## Overview
- **Agent 1**: Data Ingestion Specialist
- **Agent 2**: Data Analysis Agent  
- **Agent 3**: Report Generator
- **Agent 4**: Quality Reviewer

## Execution
Run this workflow step by step, or use the individual agent files.

## Agent 1: Data Ingestion
@import agents/data_ingestion_agent.md

Execute the data ingestion process on files in `data/input/`.

---

## Agent 2: Analysis (Wait for Agent 1)
First, check if `data/processed/ready.flag` exists. If not, stop here and ask me to run Agent 1 first.

@import agents/analysis_agent.md

Load the cleaned data and perform statistical analysis.

---

## Agent 3: Report Generation (Wait for Agent 2)  
Check if `data/processed/analysis_complete.flag` exists.

@import agents/report_agent.md

Generate the final report based on analysis results.

---

## Agent 4: Quality Review
@import agents/quality_reviewer.md

Review all outputs for completeness and accuracy.
""",

        # Individual agent files
        "agents/data_ingestion_agent.md": """# Data Ingestion Specialist

## Core Identity
- **Role**: Ingest, validate, and clean raw data files
- **Expertise**: Data validation, format conversion, error detection
- **Scope**: Only handles data input - does not perform analysis

## Input Requirements
- **Expected Input**: CSV, JSON, or Excel files in `/data/input/` directory
- **Prerequisites**: Files must exist and be readable
- **Dependencies**: None (first in pipeline)

## Processing Instructions

### Primary Tasks
1. Scan `data/input/` directory for new data files
2. Validate file formats and detect encoding issues
3. Perform basic data quality checks (null values, duplicates, outliers)
4. Standardize column names and data types
5. Generate data quality report

### Implementation
```python
import pandas as pd
import json
import os
from pathlib import Path
import logging

def setup_logging():
    logging.basicConfig(
        filename='logs/data_ingestion.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def ingest_data():
    setup_logging()
    logging.info("Starting data ingestion process")
    
    # Create output directories
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    input_dir = Path("data/input")
    if not input_dir.exists():
        logging.error("Input directory does not exist")
        return False
    
    processed_files = []
    quality_issues = []
    
    for file_path in input_dir.glob("*.csv"):
        logging.info(f"Processing {file_path}")
        
        try:
            # Read data
            df = pd.read_csv(file_path)
            original_shape = df.shape
            
            # Basic quality checks
            missing_pct = (df.isnull().sum() / len(df) * 100)
            high_missing_cols = missing_pct[missing_pct > 5].index.tolist()
            
            if high_missing_cols:
                quality_issues.append(f"High missing values in {file_path}: {high_missing_cols}")
            
            # Clean data
            df = df.drop_duplicates()
            
            # Standardize column names
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            
            # Save cleaned data
            output_path = f"data/processed/clean_{file_path.name}"
            df.to_csv(output_path, index=False)
            
            processed_files.append({
                "source_file": str(file_path),
                "output_file": output_path,
                "original_rows": original_shape[0],
                "processed_rows": len(df),
                "columns": df.columns.tolist(),
                "quality_issues": high_missing_cols
            })
            
            logging.info(f"Successfully processed {file_path}")
            
        except Exception as e:
            logging.error(f"Error processing {file_path}: {str(e)}")
            quality_issues.append(f"Failed to process {file_path}: {str(e)}")
    
    # Create metadata
    metadata = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "processed_files": processed_files,
        "quality_issues": quality_issues,
        "status": "completed" if processed_files else "failed"
    }
    
    with open("data/processed/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Signal completion
    if processed_files:
        Path("data/processed/ready.flag").touch()
        logging.info("Data ingestion completed successfully")
        return True
    else:
        logging.error("No files were successfully processed")
        return False

# Execute the agent
if __name__ == "__main__":
    success = ingest_data()
    if success:
        print("✅ Data Ingestion Agent completed successfully")
        print("📁 Check data/processed/ for cleaned files")
        print("📊 Check logs/data_ingestion.log for details")
    else:
        print("❌ Data Ingestion Agent failed")
        print("📋 Check logs/data_ingestion.log for errors")
```

### Quality Standards
- Must handle files up to 100MB
- Detect and flag >5% missing values in any column
- Standardize all date formats to ISO 8601
- Remove or flag duplicate records

### Output Specifications
- **Format**: Clean CSV + JSON metadata file
- **Required Fields**: See metadata.json structure above
- **Naming Convention**: `clean_{original_filename}.csv`, `metadata.json`
- **Handoff Instructions**: Create `data/processed/ready.flag` file when complete

Execute this agent now to process any files in the `data/input/` directory.
""",

        "agents/analysis_agent.md": """# Data Analysis Agent

## Core Identity
- **Role**: Perform statistical analysis and generate insights
- **Expertise**: Statistical analysis, pattern recognition, hypothesis testing  
- **Scope**: Analysis only - does not create final reports

## Input Requirements
- **Expected Input**: Clean CSV from Data Ingestion Agent
- **Prerequisites**: `ready.flag` file exists in `data/processed/`
- **Dependencies**: Successful completion of Data Ingestion Agent

## Processing Instructions

### Primary Tasks
1. Load clean data and validate structure
2. Perform exploratory data analysis (EDA)
3. Calculate key statistical metrics
4. Identify trends, correlations, and anomalies
5. Test relevant hypotheses
6. Rank insights by significance

### Implementation
```python
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from scipy import stats

def setup_analysis_logging():
    logging.basicConfig(
        filename='logs/data_analysis.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def analyze_data():
    setup_analysis_logging()
    logging.info("Starting data analysis process")
    
    # Check prerequisites
    if not Path("data/processed/ready.flag").exists():
        logging.error("Data ingestion not complete - ready.flag not found")
        print("❌ Prerequisites not met: Run Data Ingestion Agent first")
        return False
    
    # Create output directories
    Path("data/analysis").mkdir(parents=True, exist_ok=True)
    Path("charts").mkdir(exist_ok=True)
    
    # Load metadata to find processed files
    with open("data/processed/metadata.json", "r") as f:
        metadata = json.load(f)
    
    analysis_results = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "files_analyzed": [],
        "summary_stats": {},
        "correlations": {},
        "trends": [],
        "anomalies": [],
        "key_insights": [],
        "charts_generated": []
    }
    
    for file_info in metadata["processed_files"]:
        try:
            # Load cleaned data
            df = pd.read_csv(file_info["output_file"])
            file_name = Path(file_info["source_file"]).stem
            
            logging.info(f"Analyzing {file_name}")
            
            # Basic statistics
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                summary_stats = df[numeric_cols].describe().to_dict()
                analysis_results["summary_stats"][file_name] = summary_stats
                
                # Correlation analysis
                if len(numeric_cols) > 1:
                    corr_matrix = df[numeric_cols].corr()
                    
                    # Find strong correlations
                    strong_corr = []
                    for i in range(len(corr_matrix.columns)):
                        for j in range(i+1, len(corr_matrix.columns)):
                            corr_val = corr_matrix.iloc[i, j]
                            if abs(corr_val) > 0.7:
                                strong_corr.append({
                                    "var1": corr_matrix.columns[i],
                                    "var2": corr_matrix.columns[j],
                                    "correlation": corr_val
                                })
                    
                    analysis_results["correlations"][file_name] = strong_corr
                    
                    # Create correlation heatmap
                    plt.figure(figsize=(10, 8))
                    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
                    plt.title(f'Correlation Matrix - {file_name}')
                    chart_path = f'charts/correlation_{file_name}.png'
                    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    analysis_results["charts_generated"].append(chart_path)
                
                # Detect anomalies (simple z-score method)
                anomalies = []
                for col in numeric_cols:
                    z_scores = np.abs(stats.zscore(df[col].dropna()))
                    outliers = df[z_scores > 3][col]
                    if len(outliers) > 0:
                        anomalies.append({
                            "column": col,
                            "outlier_count": len(outliers),
                            "outlier_percentage": len(outliers) / len(df) * 100
                        })
                
                analysis_results["anomalies"].extend(anomalies)
                
                # Generate distribution plots
                for col in numeric_cols[:4]:  # Limit to first 4 numeric columns
                    plt.figure(figsize=(8, 6))
                    plt.hist(df[col].dropna(), bins=30, alpha=0.7, edgecolor='black')
                    plt.title(f'Distribution of {col} - {file_name}')
                    plt.xlabel(col)
                    plt.ylabel('Frequency')
                    chart_path = f'charts/dist_{file_name}_{col}.png'
                    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    analysis_results["charts_generated"].append(chart_path)
            
            # Key insights generation
            insights = []
            if len(numeric_cols) > 0:
                insights.append(f"Dataset contains {len(numeric_cols)} numeric variables")
                insights.append(f"Dataset has {len(df)} records after cleaning")
                
                if analysis_results["correlations"].get(file_name):
                    insights.append(f"Found {len(analysis_results['correlations'][file_name])} strong correlations")
                
                if anomalies:
                    total_anomalies = sum(a["outlier_count"] for a in anomalies)
                    insights.append(f"Detected {total_anomalies} potential anomalies")
            
            analysis_results["key_insights"].extend(insights)
            analysis_results["files_analyzed"].append(file_name)
            
            logging.info(f"Successfully analyzed {file_name}")
            
        except Exception as e:
            logging.error(f"Error analyzing {file_info['source_file']}: {str(e)}")
    
    # Save analysis results
    with open("data/analysis/analysis_results.json", "w") as f:
        json.dump(analysis_results, f, indent=2)
    
    # Signal completion
    if analysis_results["files_analyzed"]:
        Path("data/processed/analysis_complete.flag").touch()
        logging.info("Data analysis completed successfully")
        return True
    else:
        logging.error("No files were successfully analyzed")
        return False

# Execute the agent
if __name__ == "__main__":
    success = analyze_data()
    if success:
        print("✅ Data Analysis Agent completed successfully")
        print("📊 Check data/analysis/analysis_results.json for insights")
        print("📈 Check charts/ directory for visualizations")
        print("📋 Check logs/data_analysis.log for details")
    else:
        print("❌ Data Analysis Agent failed")
        print("📋 Check logs/data_analysis.log for errors")
```

### Quality Standards
- All statistical tests must include confidence intervals
- Flag any correlations >0.7 or <-0.7 as significant
- Include sample sizes for all calculations
- Validate assumptions before applying statistical tests

### Output Specifications
- **Format**: JSON analysis results + charts as PNG files
- **Required Fields**: See analysis_results.json structure above
- **Handoff Instructions**: Save analysis.json and create `analysis_complete.flag`

Execute this agent only after the Data Ingestion Agent has completed.
""",

        "agents/report_agent.md": """# Report Generator Agent

## Core Identity
- **Role**: Generate comprehensive reports from analysis results
- **Expertise**: Technical writing, data visualization, executive summaries
- **Scope**: Report creation only - does not perform analysis

## Input Requirements
- **Expected Input**: Analysis results from Data Analysis Agent
- **Prerequisites**: `analysis_complete.flag` exists in `data/processed/`
- **Dependencies**: Successful completion of Data Analysis Agent

## Processing Instructions

### Primary Tasks
1. Load analysis results and validate completeness
2. Generate executive summary
3. Create detailed findings section
4. Include visualizations and charts
5. Generate actionable recommendations
6. Create both technical and executive versions

### Implementation
```python
import json
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

def setup_report_logging():
    logging.basicConfig(
        filename='logs/report_generation.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def generate_report():
    setup_report_logging()
    logging.info("Starting report generation process")
    
    # Check prerequisites
    if not Path("data/processed/analysis_complete.flag").exists():
        logging.error("Data analysis not complete - analysis_complete.flag not found")
        print("❌ Prerequisites not met: Run Data Analysis Agent first")
        return False
    
    # Create output directory
    Path("reports").mkdir(parents=True, exist_ok=True)
    
    # Load analysis results
    try:
        with open("data/analysis/analysis_results.json", "r") as f:
            analysis = json.load(f)
        
        with open("data/processed/metadata.json", "r") as f:
            metadata = json.load(f)
    except FileNotFoundError as e:
        logging.error(f"Required analysis files not found: {str(e)}")
        return False
    
    # Generate report timestamp
    report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create executive summary
    exec_summary = generate_executive_summary(analysis, metadata)
    
    # Create technical report
    technical_report = generate_technical_report(analysis, metadata)
    
    # Save reports
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Executive Summary (Markdown)
    exec_path = f"reports/executive_summary_{timestamp_str}.md"
    with open(exec_path, "w") as f:
        f.write(exec_summary)
    
    # Technical Report (Markdown)
    tech_path = f"reports/technical_report_{timestamp_str}.md"
    with open(tech_path, "w") as f:
        f.write(technical_report)
    
    # Create report index
    report_index = {
        "timestamp": report_timestamp,
        "executive_summary": exec_path,
        "technical_report": tech_path,
        "charts_included": analysis.get("charts_generated", []),
        "files_analyzed": analysis.get("files_analyzed", []),
        "status": "completed"
    }
    
    with open("reports/report_index.json", "w") as f:
        json.dump(report_index, f, indent=2)
    
    # Signal completion
    Path("data/processed/reports_complete.flag").touch()
    logging.info("Report generation completed successfully")
    
    print(f"✅ Report Generator Agent completed successfully")
    print(f"📄 Executive Summary: {exec_path}")
    print(f"📋 Technical Report: {tech_path}")
    print(f"📊 Charts available in: charts/")
    
    return True

def generate_executive_summary(analysis, metadata):
    summary = f"""# Executive Summary - Data Analysis Report

**Generated:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

## Overview
This report presents findings from the automated analysis of {len(analysis.get('files_analyzed', []))} dataset(s) processed through our multi-agent data pipeline.

## Key Findings

### Data Quality
- **Files Processed:** {len(metadata.get('processed_files', []))}
- **Total Records:** {sum(f.get('processed_rows', 0) for f in metadata.get('processed_files', []))}
- **Quality Issues Identified:** {len(metadata.get('quality_issues', []))}

### Statistical Insights
{generate_insights_summary(analysis)}

### Anomalies and Outliers
{generate_anomalies_summary(analysis)}

## Recommendations

{generate_recommendations(analysis)}

## Next Steps
1. Review detailed technical report for complete analysis
2. Investigate flagged anomalies and data quality issues
3. Consider additional data collection for identified gaps
4. Implement recommended data quality improvements

---
*This report was generated automatically by the Multi-Agent Data Analysis System*
"""
    return summary

def generate_technical_report(analysis, metadata):
    report = f"""# Technical Data Analysis Report

**Generated:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

## Methodology
This analysis was performed using a multi-agent workflow consisting of:
1. **Data Ingestion Agent** - Data cleaning and validation
2. **Data Analysis Agent** - Statistical analysis and pattern detection
3. **Report Generator Agent** - Comprehensive reporting

## Data Processing Summary

### Files Processed
"""
    
    for file_info in metadata.get('processed_files', []):
        report += f"""
**{file_info['source_file']}**
- Original rows: {file_info['original_rows']}
- Processed rows: {file_info['processed_rows']}
- Columns: {len(file_info['columns'])}
- Data reduction: {((file_info['original_rows'] - file_info['processed_rows']) / file_info['original_rows'] * 100):.1f}%
"""
    
    report += f"""

## Statistical Analysis Results

### Summary Statistics
{generate_detailed_stats(analysis)}

### Correlation Analysis
{generate_correlation_details(analysis)}

### Anomaly Detection
{generate_anomaly_details(analysis)}

## Visualizations Generated
"""
    
    for chart in analysis.get('charts_generated', []):
        report += f"- {chart}\n"
    
    report += f"""

## Data Quality Assessment
{generate_quality_assessment(metadata)}

## Technical Notes
- Analysis performed using Python pandas and scipy
- Anomalies detected using z-score method (threshold: 3)
- Strong correlations defined as |r| > 0.7
- Missing value threshold for flagging: 5%

---
*Detailed logs available in logs/ directory*
"""
    
    return report

def generate_insights_summary(analysis):
    insights = analysis.get('key_insights', [])
    if not insights:
        return "No specific insights generated."
    
    summary = ""
    for insight in insights[:5]:  # Top 5 insights
        summary += f"- {insight}\n"
    
    return summary

def generate_anomalies_summary(analysis):
    anomalies = analysis.get('anomalies', [])
    if not anomalies:
        return "No significant anomalies detected."
    
    total_anomalies = sum(a.get('outlier_count', 0) for a in anomalies)
    return f"Detected {total_anomalies} potential outliers across {len(anomalies)} variables."

def generate_recommendations(analysis):
    recommendations = [
        "Investigate detected anomalies for data entry errors or genuine outliers",
        "Consider additional data validation rules for future ingestion",
        "Monitor strong correlations for potential multicollinearity issues"
    ]
    
    if analysis.get('anomalies'):
        recommendations.append("Focus quality improvement efforts on variables with high anomaly rates")
    
    return "\n".join(f"{i+1}. {rec}" for i, rec in enumerate(recommendations))

def generate_detailed_stats(analysis):
    stats_section = ""
    for file_name, stats in analysis.get('summary_stats', {}).items():
        stats_section += f"\n**{file_name}:**\n"
        for var, var_stats in stats.items():
            stats_section += f"- {var}: Mean={var_stats.get('mean', 0):.2f}, Std={var_stats.get('std', 0):.2f}\n"
    
    return stats_section if stats_section else "No statistical analysis performed."

def generate_correlation_details(analysis):
    corr_section = ""
    for file_name, correlations in analysis.get('correlations', {}).items():
        if correlations:
            corr_section += f"\n**{file_name}:**\n"
            for corr in correlations:
                corr_section += f"- {corr['var1']} ↔ {corr['var2']}: r={corr['correlation']:.3f}\n"
    
    return corr_section if corr_section else "No strong correlations detected."

def generate_anomaly_details(analysis):
    anom_section = ""
    for anomaly in analysis.get('anomalies', []):
        anom_section += f"- {anomaly['column']}: {anomaly['outlier_count']} outliers ({anomaly['outlier_percentage']:.1f}%)\n"
    
    return anom_section if anom_section else "No anomalies detected."

def generate_quality_assessment(metadata):
    quality_issues = metadata.get('quality_issues', [])
    if not quality_issues:
        return "✅ No data quality issues identified."
    
    assessment = "⚠️ Data quality issues identified:\n"
    for issue in quality_issues:
        assessment += f"- {issue}\n"
    
    return assessment

# Execute the agent
if __name__ == "__main__":
    generate_report()
```

### Output Specifications
- **Format**: Markdown reports (Executive + Technical)
- **Executive Summary**: High-level findings and recommendations
- **Technical Report**: Detailed methodology and results
- **Report Index**: JSON file tracking all generated reports

Execute this agent only after the Data Analysis Agent has completed.
""",

        "agents/quality_reviewer.md": """# Quality Reviewer Agent

## Core Identity
- **Role**: Review all workflow outputs for completeness and accuracy
- **Expertise**: Quality assurance, validation, completeness checking
- **Scope**: Review only - does not modify outputs

## Processing Instructions

### Primary Tasks
1. Validate all workflow outputs exist
2. Check data quality metrics
3. Verify report completeness
4. Generate quality assessment
5. Flag any issues for review

### Implementation
```python
import json
import pandas as pd
from pathlib import Path
import logging

def setup_qa_logging():
    logging.basicConfig(
        filename='logs/quality_review.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def quality_review():
    setup_qa_logging()
    logging.info("Starting quality review process")
    
    qa_results = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "workflow_status": "unknown",
        "completeness_check": {},
        "quality_issues": [],
        "recommendations": [],
        "overall_score": 0
    }
    
    # Check workflow completeness
    completeness = check_workflow_completeness()
    qa_results["completeness_check"] = completeness
    
    # Validate data quality
    quality_issues = validate_data_quality()
    qa_results["quality_issues"] = quality_issues
    
    # Review reports
    report_quality = review_reports()
    qa_results["report_quality"] = report_quality
    
    # Calculate overall score
    score = calculate_quality_score(completeness, quality_issues, report_quality)
    qa_results["overall_score"] = score
    
    # Generate recommendations
    recommendations = generate_qa_recommendations(qa_results)
    qa_results["recommendations"] = recommendations
    
    # Determine workflow status
    if score >= 80:
        qa_results["workflow_status"] = "excellent"
    elif score >= 60:
        qa_results["workflow_status"] = "good"
    elif score >= 40:
        qa_results["workflow_status"] = "acceptable"
    else:
        qa_results["workflow_status"] = "needs_improvement"
    
    # Save QA results
    Path("qa").mkdir(exist_ok=True)
    with open("qa/quality_assessment.json", "w") as f:
        json.dump(qa_results, f, indent=2)
    
    # Generate QA report
    generate_qa_report(qa_results)
    
    print(f"✅ Quality Review completed")
    print(f"📋 Overall Score: {score}/100 ({qa_results['workflow_status']})")
    print(f"📄 QA Report: qa/quality_report.md")
    
    return True

def check_workflow_completeness():
    required_files = {
        "data/processed/ready.flag": "Data ingestion complete",
        "data/processed/analysis_complete.flag": "Data analysis complete", 
        "data/processed/reports_complete.flag": "Report generation complete",
        "data/processed/metadata.json": "Data processing metadata",
        "data/analysis/analysis_results.json": "Analysis results",
        "reports/report_index.json": "Report index"
    }
    
    completeness = {}
    for file_path, description in required_files.items():
        exists = Path(file_path).exists()
        completeness[file_path] = {
            "exists": exists,
            "description": description
        }
    
    return completeness

def validate_data_quality():
    quality_issues = []
    
    try:
        # Check metadata for quality issues
        with open("data/processed/metadata.json", "r") as f:
            metadata = json.load(f)
        
        for issue in metadata.get("quality_issues", []):
            quality_issues.append({
                "type": "data_quality",
                "severity": "medium",
                "description": issue
            })
        
        # Check if any files failed processing
        processed_files = metadata.get("processed_files", [])
        if not processed_files:
            quality_issues.append({
                "type": "processing_failure",
                "severity": "high",
                "description": "No files were successfully processed"
            })
        
    except FileNotFoundError:
        quality_issues.append({
            "type": "missing_metadata",
            "severity": "high", 
            "description": "Data processing metadata not found"
        })
    
    return quality_issues

def review_reports():
    report_quality = {
        "reports_generated": 0,
        "charts_generated": 0,
        "completeness_score": 0
    }
    
    try:
        with open("reports/report_index.json", "r") as f:
            report_index = json.load(f)
        
        # Check if reports exist
        exec_summary = Path(report_index.get("executive_summary", ""))
        tech_report = Path(report_index.get("technical_report", ""))
        
        if exec_summary.exists():
            report_quality["reports_generated"] += 1
        if tech_report.exists():
            report_quality["reports_generated"] += 1
        
        report_quality["charts_generated"] = len(report_index.get("charts_included", []))
        
        # Calculate completeness score
        max_score = 2  # 2 reports expected
        report_quality["completeness_score"] = (report_quality["reports_generated"] / max_score) * 100
        
    except FileNotFoundError:
        report_quality["completeness_score"] = 0
    
    return report_quality

def calculate_quality_score(completeness, quality_issues, report_quality):
    # Completeness score (40% of total)
    completed_files = sum(1 for f in completeness.values() if f["exists"])
    completeness_score = (completed_files / len(completeness)) * 40
    
    # Quality issues score (30% of total)
    high_severity = sum(1 for issue in quality_issues if issue["severity"] == "high")
    medium_severity = sum(1 for issue in quality_issues if issue["severity"] == "medium")
    
    quality_penalty = (high_severity * 10) + (medium_severity * 5)
    quality_score = max(0, 30 - quality_penalty)
    
    # Report quality score (30% of total)
    report_score = (report_quality["completeness_score"] / 100) * 30
    
    total_score = completeness_score + quality_score + report_score
    return min(100, max(0, total_score))

def generate_qa_recommendations(qa_results):
    recommendations = []
    
    # Check for missing files
    for file_path, info in qa_results["completeness_check"].items():
        if not info["exists"]:
            recommendations.append(f"Missing: {file_path} - {info['description']}")
    
    # Address quality issues
    for issue in qa_results["quality_issues"]:
        if issue["severity"] == "high":
            recommendations.append(f"HIGH PRIORITY: {issue['description']}")
        else:
            recommendations.append(f"Review: {issue['description']}")
    
    # Report quality recommendations
    if qa_results["report_quality"]["reports_generated"] < 2:
        recommendations.append("Ensure both executive summary and technical report are generated")
    
    if not recommendations:
        recommendations.append("Workflow completed successfully with no major issues")
    
    return recommendations

def generate_qa_report(qa_results):
    report = f"""# Quality Assurance Report

**Generated:** {pd.Timestamp.now().strftime('%B %d, %Y at %I:%M %p')}

## Overall Assessment
- **Status:** {qa_results['workflow_status'].upper()}
- **Quality Score:** {qa_results['overall_score']}/100

## Workflow Completeness

| Component | Status | Description |
|-----------|--------|-------------|
"""
    
    for file_path, info in qa_results["completeness_check"].items():
        status = "✅ Complete" if info["exists"] else "❌ Missing"
        report += f"| {Path(file_path).name} | {status} | {info['description']} |\n"
    
    report += f"""

## Quality Issues Identified
"""
    
    if qa_results["quality_issues"]:
        for issue in qa_results["quality_issues"]:
            severity_icon = "🔴" if issue["severity"] == "high" else "🟡"
            report += f"- {severity_icon} {issue['description']}\n"
    else:
        report += "✅ No quality issues identified\n"
    
    report += f"""

## Report Quality
- **Reports Generated:** {qa_results['report_quality']['reports_generated']}/2
- **Charts Generated:** {qa_results['report_quality']['charts_generated']}
- **Completeness Score:** {qa_results['report_quality']['completeness_score']:.1f}%

## Recommendations
"""
    
    for rec in qa_results["recommendations"]:
        report += f"- {rec}\n"
    
    report += f"""

## Next Steps
Based on this assessment, consider the following actions:
1. Address any high-priority issues identified above
2. Review workflow logs for detailed error information
3. Re-run failed agents if necessary
4. Update data quality standards based on findings

---
*Generated by Quality Reviewer Agent*
"""
    
    with open("qa/quality_report.md", "w") as f:
        f.write(report)

# Execute the agent
if __name__ == "__main__":
    quality_review()
```

This agent should be run after all other agents have completed to provide a comprehensive quality assessment of the entire workflow.
""",

        # Configuration and setup files
        "config/agent_config.json": """{
  "agents": {
    "data_ingestion": {
      "name": "Data Ingestion Specialist",
      "timeout_minutes": 10,
      "retry_attempts": 3,
      "required_tools": ["pandas", "pathlib"],
      "input_formats": [".csv", ".json", ".xlsx"],
      "max_file_size_mb": 100
    },
    "data_analysis": {
      "name": "Data Analysis Agent",
      "timeout_minutes": 15,
      "retry_attempts": 2,
      "required_tools": ["pandas", "numpy", "scipy", "matplotlib", "seaborn"],
      "dependencies": ["data_ingestion"],
      "analysis_methods": ["correlation", "anomaly_detection", "summary_stats"]
    },
    "report_generation": {
      "name": "Report Generator Agent", 
      "timeout_minutes": 5,
      "retry_attempts": 2,
      "required_tools": ["pandas", "pathlib"],
      "dependencies": ["data_analysis"],
      "output_formats": ["markdown", "json"]
    },
    "quality_review": {
      "name": "Quality Reviewer Agent",
      "timeout_minutes": 5,
      "retry_attempts": 1,
      "required_tools": ["pathlib", "json"],
      "dependencies": ["data_ingestion", "data_analysis", "report_generation"],
      "quality_thresholds": {
        "excellent": 80,
        "good": 60,
        "acceptable": 40
      }
    }
  },
  "workflow": {
    "execution_order": ["data_ingestion", "data_analysis", "report_generation", "quality_review"],
    "parallel_execution": false,
    "stop_on_failure": true,
    "cleanup_temp_files": true
  },
  "logging": {
    "level": "INFO",
    "directory": "logs",
    "max_file_size_mb": 10,
    "backup_count": 5
  }
}""",

        "scripts/run_workflow.py": """#!/usr/bin/env python3
\"\"\"
Workflow orchestration script for Claude Code subagents
This script can run the entire workflow or individual agents
\"\"\"

import json
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/workflow_orchestrator.log'),
            logging.StreamHandler()
        ]
    )

def load_config():
    with open('config/agent_config.json', 'r') as f:
        return json.load(f)

def run_agent(agent_name, config):
    \"\"\"Run a specific agent using Claude Code\"\"\"
    agent_file = f"agents/{agent_name}_agent.md"
    
    if not Path(agent_file).exists():
        logging.error(f"Agent file not found: {agent_file}")
        return False
    
    logging.info(f"Running agent: {agent_name}")
    
    try:
        # Run the agent using Claude Code
        result = subprocess.run([
            'claude-code', 'run', agent_file
        ], capture_output=True, text=True, timeout=config['timeout_minutes']*60)
        
        if result.returncode == 0:
            logging.info(f"Agent {agent_name} completed successfully")
            return True
        else:
            logging.error(f"Agent {agent_name} failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error(f"Agent {agent_name} timed out")
        return False
    except Exception as e:
        logging.error(f"Error running agent {agent_name}: {str(e)}")
        return False

def run_full_workflow():
    \"\"\"Run the complete workflow\"\"\"
    setup_logging()
    config = load_config()
    
    logging.info("Starting full workflow execution")
    
    # Create necessary directories
    directories = ['data/input', 'data/processed', 'data/analysis', 'reports', 'charts', 'logs', 'qa']
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Execute agents in order
    workflow_config = config['workflow']
    execution_order = workflow_config['execution_order']
    
    for agent_name in execution_order:
        if agent_name not in config['agents']:
            logging.error(f"Agent {agent_name} not found in configuration")
            if workflow_config['stop_on_failure']:
                return False
            continue
        
        agent_config = config['agents'][agent_name]
        success = run_agent(agent_name, agent_config)
        
        if not success and workflow_config['stop_on_failure']:
            logging.error(f"Workflow stopped due to agent failure: {agent_name}")
            return False
    
    logging.info("Workflow execution completed")
    return True

def run_single_agent(agent_name):
    \"\"\"Run a single agent\"\"\"
    setup_logging()
    config = load_config()
    
    if agent_name not in config['agents']:
        logging.error(f"Agent {agent_name} not found in configuration")
        return False
    
    agent_config = config['agents'][agent_name]
    return run_agent(agent_name, agent_config)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python run_workflow.py full                    # Run complete workflow")
        print("  python run_workflow.py agent <agent_name>      # Run specific agent")
        print("  python run_workflow.py list                    # List available agents")
        return
    
    command = sys.argv[1]
    
    if command == "full":
        success = run_full_workflow()
        sys.exit(0 if success else 1)
    
    elif command == "agent":
        if len(sys.argv) < 3:
            print("Please specify agent name")
            return
        agent_name = sys.argv[2]
        success = run_single_agent(agent_name)
        sys.exit(0 if success else 1)
    
    elif command == "list":
        config = load_config()
        print("Available agents:")
        for agent_name, agent_config in config['agents'].items():
            print(f"  - {agent_name}: {agent_config['name']}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
""",

        "data/input/sample_data.csv": """id,name,age,salary,department,join_date,performance_score
1,Alice Johnson,28,65000,Engineering,2020-03-15,8.5
2,Bob Smith,34,72000,Engineering,2019-07-22,7.8
3,Carol Davis,29,58000,Marketing,2021-01-10,9.2
4,David Wilson,31,69000,Engineering,2020-11-05,8.0
5,Eve Brown,26,52000,Marketing,2022-02-14,8.7
6,Frank Miller,38,85000,Engineering,2018-05-30,9.1
7,Grace Lee,32,61000,Marketing,2021-08-17,7.9
8,Henry Taylor,27,56000,Sales,2022-06-01,8.3
9,Ivy Chen,35,78000,Engineering,2019-12-03,8.8
10,Jack Robinson,30,64000,Sales,2021-04-20,7.6
11,Kate Anderson,33,71000,Engineering,2020-09-08,8.4
12,Liam Thompson,29,59000,Marketing,2022-01-25,8.1
13,Mia Garcia,31,67000,Sales,2020-12-12,8.9
14,Noah Martinez,28,63000,Engineering,2021-03-30,7.7
15,Olivia White,36,82000,Engineering,2018-11-15,9.0""",

        "README.md": """# Claude Code Subagent Workflow Example

This project demonstrates how to structure and implement subagent workflows using Claude Code. The example implements a complete data analysis pipeline with specialized agents.

## Project Structure

```
claude-code-subagents/
├── agents/                    # Individual agent definitions
│   ├── data_ingestion_agent.md
│   ├── analysis_agent.md
│   ├── report_agent.md
│   └── quality_reviewer.md
├── config/                    # Configuration files
│   └── agent_config.json
├── scripts/                   # Utility scripts
│   └── run_workflow.py
├── data/                      # Data directories
│   ├── input/                 # Raw data files
│   ├── processed/             # Cleaned data
│   └── analysis/              # Analysis results
├── reports/                   # Generated reports
├── charts/                    # Generated visualizations
├── logs/                      # Agent execution logs
├── qa/                        # Quality assurance outputs
├── workflow.md                # Main workflow file
└── README.md                  # This file
```

## Agents Overview

### 1. Data Ingestion Specialist
- **Purpose**: Clean and validate raw data files
- **Input**: CSV/JSON/Excel files in `data/input/`
- **Output**: Cleaned CSV files and metadata in `data/processed/`
- **Signal**: Creates `ready.flag` when complete

### 2. Data Analysis Agent  
- **Purpose**: Perform statistical analysis and generate insights
- **Prerequisites**: Waits for `ready.flag` from Data Ingestion Agent
- **Output**: Analysis results JSON and visualization charts
- **Signal**: Creates `analysis_complete.flag` when done

### 3. Report Generator Agent
- **Purpose**: Create comprehensive reports from analysis
- **Prerequisites**: Waits for `analysis_complete.flag`
- **Output**: Executive summary and technical report (Markdown)
- **Signal**: Creates `reports_complete.flag`

### 4. Quality Reviewer Agent
- **Purpose**: Validate workflow completeness and quality
- **Prerequisites**: Waits for all other agents to complete
- **Output**: Quality assessment report and scoring

## Getting Started

### Prerequisites
- Claude Code CLI tool installed
- Python 3.7+ with required packages:
  - pandas
  - numpy
  - matplotlib
  - seaborn
  - scipy

### Installation
1. Extract this zip file to your desired location
2. Navigate to the project directory
3. Install Python dependencies:
   ```bash
   pip install pandas numpy matplotlib seaborn scipy
   ```

### Usage Options

#### Option 1: Run Complete Workflow
```bash
claude-code run workflow.md
```

#### Option 2: Run Individual Agents
```bash
# Run agents step by step
claude-code run agents/data_ingestion_agent.md
claude-code run agents/analysis_agent.md
claude-code run agents/report_agent.md
claude-code run agents/quality_reviewer.md
```

#### Option 3: Use Orchestration Script
```bash
# Run full workflow
python scripts/run_workflow.py full

# Run specific agent
python scripts/run_workflow.py agent data_ingestion

# List available agents
python scripts/run_workflow.py list
```

## Adding Your Own Data

1. Place your CSV, JSON, or Excel files in the `data/input/` directory
2. Run the workflow using any of the methods above
3. Check results in:
   - `data/processed/` - Cleaned data and metadata
   - `data/analysis/` - Analysis results and insights
   - `reports/` - Generated reports
   - `charts/` - Visualization charts
   - `qa/` - Quality assessment

## Customizing Agents

### Modifying Existing Agents
Edit the agent markdown files in the `agents/` directory to customize:
- Processing logic
- Quality standards
- Output formats
- Analysis methods

### Adding New Agents
1. Create a new `.md` file in `agents/` directory
2. Follow the agent template structure (see existing agents)
3. Update `config/agent_config.json` with new agent configuration
4. Add to workflow execution order in `workflow.md`

### Configuration
Modify `config/agent_config.json` to adjust:
- Agent timeouts and retry attempts
- Tool dependencies
- Quality thresholds
- Workflow execution order

## Agent Communication Patterns

### File-Based Signaling
Agents communicate through flag files:
- `ready.flag` - Data ingestion complete
- `analysis_complete.flag` - Analysis complete  
- `reports_complete.flag` - Reports complete

### Shared State
Agents share data through:
- JSON metadata files
- Processed data files
- Shared directory structure
- Status logging

### Prerequisites Checking
Each agent validates prerequisites before execution:
```python
if not Path("data/processed/ready.flag").exists():
    print("Prerequisites not met")
    return False
```

## Monitoring and Debugging

### Logs
Each agent generates detailed logs in `logs/`:
- `data_ingestion.log`
- `data_analysis.log`  
- `report_generation.log`
- `quality_review.log`
- `workflow_orchestrator.log`

### Quality Assurance
The Quality Reviewer Agent provides:
- Completeness checking
- Quality scoring (0-100)
- Issue identification
- Recommendations for improvement

### Status Tracking
Monitor workflow progress through:
- Flag files in `data/processed/`
- Log files with timestamps
- Quality assessment reports

## Best Practices

### Agent Design
- **Single Responsibility**: Each agent has one clear purpose
- **Clear Interfaces**: Well-defined inputs/outputs
- **Error Handling**: Robust error detection and logging
- **Validation**: Check prerequisites before execution

### Workflow Organization
- **Sequential Dependencies**: Clear execution order
- **State Management**: Persistent state through files
- **Idempotency**: Agents can be safely re-run
- **Monitoring**: Comprehensive logging and status tracking

### Extensibility
- **Modular Design**: Easy to add/remove agents
- **Configuration-Driven**: Behavior controlled through config files
- **Standardized Communication**: Consistent signaling patterns
- **Quality Gates**: Built-in quality assurance

## Troubleshooting

### Common Issues

**Agent Not Starting**
- Check if prerequisites (flag files) exist
- Verify input data is in correct location
- Check logs for detailed error messages

**Processing Failures**
- Review agent-specific log files
- Check data format compatibility
- Verify required Python packages are installed

**Quality Issues**
- Run Quality Reviewer Agent for assessment
- Check QA report for specific recommendations
- Review data quality metrics in metadata files

### Recovery Strategies
- Agents can be re-run individually after fixing issues
- Use flag files to track which agents need re-execution
- Check orchestration script for automated retry logic

## Advanced Features

### Parallel Execution
Modify `config/agent_config.json` to enable parallel execution where dependencies allow.

### Dynamic Routing
Extend agents with conditional logic based on data characteristics.

### Custom Analysis
Add domain-specific analysis methods to the Data Analysis Agent.

### Report Customization
Modify report templates in the Report Generator Agent for your specific needs.

## Contributing

When extending this workflow:
1. Follow the established agent template structure
2. Add comprehensive logging and error handling
3. Update configuration files appropriately
4. Document any new dependencies or requirements
5. Test agent interactions and communication patterns

---

This example provides a foundation for building sophisticated multi-agent workflows in Claude Code. Adapt and extend it based on your specific use cases and requirements.
""",

        "requirements.txt": """pandas>=1.5.0
numpy>=1.21.0
matplotlib>=3.5.0
seaborn>=0.11.0
scipy>=1.9.0
pathlib2>=2.3.7
""",

        ".gitignore": """# Data files
data/input/*.csv
data/input/*.xlsx
data/input/*.json
data/processed/*
data/analysis/*

# Generated outputs
reports/*
charts/*
logs/*
qa/*

# Keep structure but ignore contents
!data/input/sample_data.csv
!data/processed/.gitkeep
!data/analysis/.gitkeep
!reports/.gitkeep
!charts/.gitkeep
!logs/.gitkeep
!qa/.gitkeep

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
""",

        # Keep directory structure with placeholder files
        "data/processed/.gitkeep": "",
        "data/analysis/.gitkeep": "",
        "reports/.gitkeep": "",
        "charts/.gitkeep": "",
        "logs/.gitkeep": "",
        "qa/.gitkeep": "",
    }
    
    # Create the zip file
    zip_filename = "claude_code_subagent_workflow.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path, content in files_to_create.items():
            # Ensure directory structure in zip
            zipf.writestr(f"claude-code-subagents/{file_path}", content)
    
    print(f"✅ Created {zip_filename}")
    print(f"📁 Contains {len(files_to_create)} files")
    print("\n📋 Project Structure:")
    
    # Show structure
    dirs = set()
    for file_path in files_to_create.keys():
        parts = Path(file_path).parts
        for i in range(len(parts)):
            dirs.add("/".join(parts[:i+1]))
    
    for dir_path in sorted(dirs):
        if not dir_path.endswith('.gitkeep') and not dir_path.endswith(('.md', '.py', '.json', '.csv', '.txt')):
            level = dir_path.count('/')
            indent = "  " * level
            name = Path(dir_path).name
            print(f"{indent}📁 {name}/")
        elif '.' in Path(dir_path).name:
            level = dir_path.count('/')
            indent = "  " * level
            name = Path(dir_path).name
            print(f"{indent}📄 {name}")
    
    return zip_filename

if __name__ == "__main__":
    create_workflow_zip()
