"""KQL query to URL converter CLI tool."""

import argparse
import base64
import gzip
from pathlib import Path


def generate_kusto_query_link(cluster: str, database: str, query: str) -> str:
    """Generate a link to a given Kusto query in Azure Data Explorer."""

    encoded_bytes = gzip.compress(query.encode("utf-8"))
    encoded_query = base64.b64encode(encoded_bytes).decode("utf-8")

    return f"https://dataexplorer.azure.com/clusters/{cluster}/databases/{database}?query={encoded_query}"


def cli():
    """Command-line interface for KQL to URL conversion."""

    # Create the argument parser
    parser = argparse.ArgumentParser(
        prog="kql2url",
        description="KQL query to URL converter CLI tool."
    )

    # Add arguments
    parser.add_argument("-c", "--cluster",
                        type=str,
                        required=True,
                        help="Cluster name")

    parser.add_argument("-d","--database",
                        type=str,
                        required=True,
                        help="Database name")

    parser.add_argument("-q", "--query",
                        type=str,
                        required=False,
                        help="SQL query to convert to url")

    parser.add_argument("-f", "--kql-file",
                        type=str,
                        required=False,
                        help="Path to a file containing the KQL query")

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        help="Enable verbose output")

    # Parse the arguments
    args = parser.parse_args()

    # If a KQL file is provided, read the query from the file
    # If no query is provided, raise an error
    if not args.query and not args.kql_file:
        parser.error("No query provided. Please specify a query or a KQL file.")

    if args.kql_file:
        kql_path = Path(args.kql_file)
        if not kql_path.exists():
            parser.error(f"KQL file path does not exist: {args.kql_file}")

        if not kql_path.is_file():
            parser.error(f"KQL file path is not a file: {args.kql_file}")

        with open(args.kql_file, "r") as fp:
            query = fp.read()
    else:
        query = args.query

    # Access the arguments
    database = args.database
    cluster = args.cluster
    verbose = args.verbose

    if verbose:
        print(f"Cluster: {cluster}")
        print(f"Database: {database}")
        print(f"Query: {query}")
        print("")

    url = generate_kusto_query_link(cluster, database, query)

    if verbose:
        print(f"Generated URL: {url}")
    else:
        print(url)


if __name__ == "__main__":
    cli()
