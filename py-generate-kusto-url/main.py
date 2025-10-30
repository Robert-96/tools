import argparse
import base64
import gzip


def generate_kusto_query_link(cluster: str, database: str, query: str) -> str:
    """Generate a link to a given Kusto query in Azure Data Explorer."""

    encoded_bytes = gzip.compress(query.encode('utf-8'))
    encoded_query = base64.b64encode(encoded_bytes).decode('utf-8')

    return f"https://dataexplorer.azure.com/clusters/{cluster}/{database}?query={encoded_query}"


def cli():
    # Create the argument parser
    parser = argparse.ArgumentParser(description='Database query tool')
    
    # Add arguments
    parser.add_argument('--cluster', 
                        type=str, 
                        required=True,
                        help='Cluster name')
    
    parser.add_argument('--database', 
                        type=str, 
                        required=True,
                        help='Database name')
    
    parser.add_argument('--query', 
                        type=str, 
                        required=True,
                        help='SQL query to convert to url')
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Access the arguments
    database = args.database
    cluster = args.cluster
    query = args.query
    
    # Print the parsed arguments (replace with your logic)
    print(f"Cluster: {cluster}")
    print(f"Database: {database}")
    print(f"Query: {query}")

    url = generate_kusto_query_link(cluster, database, query)

    print(f"Url: {url}")


if __name__ == "__main__": 
    cli() 
