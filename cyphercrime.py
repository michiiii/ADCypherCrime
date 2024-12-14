import argparse
import json
import getpass
import os
import time
from neo4j import GraphDatabase
from datetime import datetime
from colorama import Fore, Style, init

def banner():
    font = """
 █████  ██████       ██████ ██    ██ ██████  ██   ██ ███████ ██████       ██████ ██████  ██ ███    ███ ███████ 
██   ██ ██   ██     ██       ██  ██  ██   ██ ██   ██ ██      ██   ██     ██      ██   ██ ██ ████  ████ ██      
███████ ██   ██     ██        ████   ██████  ███████ █████   ██████      ██      ██████  ██ ██ ████ ██ █████   
██   ██ ██   ██     ██         ██    ██      ██   ██ ██      ██   ██     ██      ██   ██ ██ ██  ██  ██ ██      
██   ██ ██████       ██████    ██    ██      ██   ██ ███████ ██   ██      ██████ ██   ██ ██ ██      ██ ███████ 

by Michael Ritter
"""
    print(font)

# Initialize Colorama
init(autoreset=True)

def format_timestamp():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Script to execute Cypher queries on a Neo4j database.')
    parser.add_argument(
        '--url', 
        type=str, 
        default='neo4j://localhost:7687', 
        help='URL for connecting to the Neo4j database. Defaults to "neo4j://localhost:7687".'
    )
    parser.add_argument(
        '--queries_dir', 
        type=str, 
        default='queries', 
        help='Path to the directory containing JSON files with Cypher queries. Defaults to "queries".'
    )
    parser.add_argument(
        '--username', 
        type=str, 
        default='neo4j', 
        help='Username for the Neo4j database. Defaults to "neo4j".'
    )
    parser.add_argument(
        '--password', 
        type=str, 
        default=None, 
        help='Password for the Neo4j database. If not provided, the script will prompt for it.'
    )
    parser.add_argument(
        '--out_path', 
        type=str, 
        default='Report', 
        help='Output directory path where the results will be stored. Defaults to a directory named "Report".'
    )
    args = parser.parse_args()

    if args.password is None:
        args.password = getpass.getpass("Enter password for Neo4j database: ")

    # Check and create output directory if it doesn't exist
    ensure_directory_exists(args.out_path)
    
    return args

def ensure_directory_exists(directory_path):
    if not os.path.exists(directory_path):
        print(f"Creating directory: {directory_path}")
        os.makedirs(directory_path)

def check_file_existence(file_path):
    if not os.path.exists(file_path):
        print(f"{file_path} does not exist.")
        return False
    return True

def load_queries_from_directory(directory_path):
    queries = []

    if not os.path.exists(directory_path):
        print(f"Queries directory '{directory_path}' does not exist.")
        return None

    for file_name in os.listdir(directory_path):
        if file_name.endswith('.json'):
            file_path = os.path.join(directory_path, file_name)
            try:
                with open(file_path, 'r') as file:
                    query_data = json.load(file)
                    queries.extend(query_data.get("queries", []))
            except json.JSONDecodeError:
                print(f"Query file '{file_name}' is not valid JSON.")
            except KeyError:
                print(f"Invalid query file structure in '{file_name}'. Expected 'queries' key.")
    
    return queries if queries else None

def execute_queries(driver, queries):
    results = []
    num_successful = 0
    num_failed = 0

    for query_obj in queries:
        query_name = query_obj["name"]
        query = query_obj["query"]
        print(f"{format_timestamp()} {Style.BRIGHT}[Info]{Style.RESET_ALL} Query '{query_name}'")

        start_time = time.time()

        try:
            with driver.session() as session:
                records = session.run(query).data()
                end_time = time.time()

                formatted_result = {
                    'Category': query_obj['category'],
                    'QueryName': query_name,
                    'ShortName': query_obj['shortname'],
                    'CypherQuery': json.dumps({"statements": [{"statement": query}]}),
                    'Result': records
                }
                results.append(formatted_result)
                num_successful += 1

                print(f"{format_timestamp()} {Fore.GREEN}{Style.BRIGHT}[Successful]{Style.RESET_ALL} Successfully executed query '{query_name}'. Runtime: {end_time - start_time:.2f} seconds, Records: {len(records)}")

        except Exception as e:
            end_time = time.time()
            print(f"{format_timestamp()} {Fore.RED}{Style.BRIGHT}[Failed]{Style.RESET_ALL} Failed to execute query '{query_name}': {e}. Runtime: {end_time - start_time:.2f} seconds.")
            num_failed += 1
            continue

    # Sort results by category
    results.sort(key=lambda x: x['Category'])

    return results, num_successful, num_failed

def export_cypher_crime_html(cypher_data, report_directory):
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not os.path.exists(report_directory):
        os.makedirs(report_directory)

    grouped_data = {}
    for data in cypher_data:
        category = data['Category']
        if category in grouped_data:
            grouped_data[category].append(data)
        else:
            grouped_data[category] = [data]

    nav_items = ''
    for category in grouped_data.keys():
        safe_category = category.replace(' ', '_')
        nav_items += f"<li class='nav-item'><a class='nav-link' href='./{safe_category}.html'>{category}</a></li>"

    for category, data in grouped_data.items():
        safe_category = category.replace(' ', '_')
        file_name = os.path.join(report_directory, f'{safe_category}.html')

        html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} - AD Cypher Crime Results</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.10.20/css/dataTables.bootstrap4.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css">
    <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>
    <script src="https://cdn.datatables.net/1.10.20/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.10.20/js/dataTables.bootstrap4.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
    <style>
        pre {{
            background-color: #f4f4f4;
            border: 1px solid #ddd;
            display: inline-block;
        }}
        code {{
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>

<nav class='navbar navbar-expand-lg navbar-light bg-light'>
    <a class='navbar-brand' href='#'>AD Cypher Crime Reports</a>
    <button class='navbar-toggler' type='button' data-toggle='collapse' data-target='#navbarNav' aria-controls='navbarNav' aria-expanded='false' aria-label='Toggle navigation'>
        <span class='navbar-toggler-icon'></span>
    </button>
    <div class='collapse navbar-collapse' id='navbarNav'>
        <ul class='navbar-nav'>
            {nav_items}
        </ul>
    </div>
</nav>

<div class="accordion" id="accordionExample">
'''

        for result in data:
            query_name = result['QueryName']
            short_name = result['ShortName']
            cypher_query = json.loads(result['CypherQuery']).get('statements', [{}])[0].get('statement', '')

            if result['Result'] and len(result['Result']) > 0:
                columns = result['Result'][0].keys()
                table_headers = ''.join([f"<th>{column}</th>" for column in columns])

                table_rows = ''
                for row in result['Result']:
                    cells = [f"<td>{row[column]}</td>" for column in columns]
                    table_rows += f"<tr>{''.join(cells)}</tr>"

                html_content += f'''
<div class='card'>
    <div class='card-header' id='heading{short_name}'>
        <h2 class='mb-0'>
            <button class='btn btn-link' type='button' data-toggle='collapse' data-target='#collapse{short_name}' aria-expanded='true' aria-controls='collapse{short_name}'>
                {query_name}
            </button>
        </h2>
    </div>
    <div id='collapse{short_name}' class='collapse' aria-labelledby='heading{short_name}' data-parent='#accordionExample'>
        <div class='card-body'>
        
        <p><strong>Cypher-Query:</strong></p>
        <pre>
            <code class="language-sql">
{cypher_query}
            </code>
        </pre>    
            <table class='table table-striped table-bordered' id='table{short_name}'>
                <thead>
                    <tr>{table_headers}</tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
</div>
'''
            else:
                html_content += f'''
<div class='card'>
    <div class='card-header' id='heading{short_name}'>
        <h2 class='mb-0'>
            <button class='btn btn-link' type='button' data-toggle='collapse' data-target='#collapse{short_name}' aria-expanded='true' aria-controls='collapse{short_name}'>
                {query_name}
            </button>
        </h2>
    </div>
    <div id='collapse{short_name}' class='collapse' aria-labelledby='heading{short_name}' data-parent='#accordionExample'>
        <div class='card-body'>
            No data found.
        </div>
    </div>
</div>
'''

        html_content += '''

</div>

<script>
$(document).ready(function() {
    $('.table').DataTable({
        'lengthMenu': [ [10, 25, 50, -1], [10, 25, 50, 'All'] ],
        'pageLength': 10,
        'searching': true,
        'ordering': true
    });
});
</script>

</body>
</html>
'''

        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(html_content)

def main():
    banner()
    args = parse_arguments()

    queries = load_queries_from_directory(args.queries_dir)
    if queries is None:
        return

    driver = GraphDatabase.driver(args.url, auth=(args.username, args.password))

    total_start_time = time.time()
    results, num_successful, num_failed = execute_queries(driver, queries)
    driver.close()
    total_end_time = time.time()

    # Call the export function
    export_cypher_crime_html(results, args.out_path)

    print(f"Total execution time: {total_end_time - total_start_time} seconds")
    print(f"Total number of queries: {len(queries)}")
    print(f"Number of successful queries: {num_successful}")
    print(f"Number of failed queries: {num_failed}")

if __name__ == "__main__":
    main()
