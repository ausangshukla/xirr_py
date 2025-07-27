import json
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import markdown
from bs4 import BeautifulSoup

def generate_html_report(json_report_path: str, output_html_path: str, template_file: str = 'templates/report_template.html'):
    """
    Generates a well-formatted HTML report from a JSON analysis report,
    including tabular data and charts.

    Args:
        json_report_path (str): The file path to the input JSON report.
        output_html_path (str): The full file path for the output HTML document.
    """
    try:
        with open(json_report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)

        # Set up Jinja2 environment
        env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))

        # Add a filter to convert markdown to HTML
        def markdown_to_html(md_text):
            return markdown.markdown(md_text)
        env.filters['markdown_to_html'] = markdown_to_html

        template = env.get_template(template_file)

        # Render the template
        html_content = template.render(report_data=report_data, datetime=datetime)

        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML report successfully generated at '{output_html_path}'")

    except FileNotFoundError:
        print(f"Error: JSON report file not found at '{json_report_path}'")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{json_report_path}'. Ensure it's a valid JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

