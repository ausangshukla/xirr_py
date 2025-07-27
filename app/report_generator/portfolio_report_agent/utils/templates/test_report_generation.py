import json
import os
from langgraph_agent.src.utils.report_generator import generate_html_report

def create_sample_json_report(output_path):
    """Creates a sample JSON report for testing purposes."""
    sample_report_data = [
        {
            "section": "Executive Summary",
            "content": "This is an **executive summary** of the portfolio analysis. It highlights key findings and recommendations. This section demonstrates the markdown widget.",
            "key_highlights": [
                "Overall portfolio performance was strong, exceeding benchmarks by 5%.",
                "Technology sector investments showed significant growth.",
                "Identified areas for risk mitigation in emerging markets."
            ]
        },
        {
            "section": "Financial Performance Overview",
            "tabular_data": {
                "title": "Quarterly Revenue (in millions USD)",
                "rows": [
                    {"Quarter": "Q1 2024", "Revenue": 120, "Growth": "10%"},
                    {"Quarter": "Q2 2024", "Revenue": 135, "Growth": "12.5%"},
                    {"Quarter": "Q3 2024", "Revenue": 140, "Growth": "3.7%"},
                    {"Quarter": "Q4 2024", "Revenue": 155, "Growth": "10.7%"}
                ]
            },
            "graph_specs": [
                {
                    "title": "Quarterly Revenue Trend",
                    "type": "line",
                    "data": {
                        "labels": ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"],
                        "datasets": [{
                            "label": "Revenue",
                            "data": [120, 135, 140, 155],
                            "borderColor": "rgb(75, 192, 192)",
                            "tension": 0.1
                        }]
                    }
                },
                {
                    "title": "Investment Allocation by Sector",
                    "type": "pie",
                    "data": {
                        "labels": ["Technology", "Healthcare", "Finance", "Energy"],
                        "datasets": [{
                            "label": "Allocation",
                            "data": [40, 25, 20, 15],
                            "backgroundColor": [
                                "rgb(255, 99, 132)",
                                "rgb(54, 162, 235)",
                                "rgb(255, 205, 86)",
                                "rgb(75, 192, 192)"
                            ],
                            "hoverOffset": 4
                        }]
                    }
                }
            ]
        },
        {
            "section": "Detailed Analysis",
            "sub_sections": [
                {
                    "title": "Technology Sector Deep Dive",
                    "content": "The **technology sector** showed robust growth, driven by strong demand for cloud services and AI innovations. Key players in this sector contributed significantly to the overall portfolio gains."
                },
                {
                    "title": "Risk Assessment and Mitigation",
                    "content": "A detailed *risk assessment* identified potential vulnerabilities in emerging markets due to currency fluctuations. Mitigation strategies include diversification and hedging."
                }
            ]
        }
    ]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_report_data, f, indent=4)
    print(f"Sample JSON report created at '{output_path}'")

if __name__ == "__main__":
    # Define paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Adjusting paths to be relative to the project root for consistency
    # The report_generator expects template_file relative to its own directory
    # So, 'templates/report_template.html' is correct for generate_html_report
    
    json_output_dir = os.path.join(current_dir, "data")
    os.makedirs(json_output_dir, exist_ok=True)
    sample_json_path = os.path.join(json_output_dir, "sample_report.json")
    
    html_output_dir = os.path.join(current_dir, "outputs")
    os.makedirs(html_output_dir, exist_ok=True)
    output_html_path = os.path.join(html_output_dir, "sample_report.html")

    # Create sample JSON
    create_sample_json_report(sample_json_path)

    # Generate HTML report
    # The template_file path is relative to the report_generator.py's directory
    # which is langgraph_agent/src/utils
    generate_html_report(
        json_report_path=sample_json_path,
        output_html_path=output_html_path,
        template_file='templates/report_template.html'
    )