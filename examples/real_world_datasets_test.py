#!/usr/bin/env python
"""
Test script for working with real-world datasets in Graphem.

This script demonstrates how to download, load, and analyze real-world graph datasets
from various sources including SNAP, Network Repository, and Semantic Scholar.
"""

import os
import time
import numpy as np
import networkx as nx
import pandas as pd
import plotly.express as px
from pathlib import Path

from graphem.embedder import GraphEmbedder
from graphem.datasets import (
    list_available_datasets,
    load_dataset,
    load_dataset_as_networkx,
    SNAPDataset
)
from graphem.visualization import report_full_correlation_matrix, plot_radial_vs_centrality


def print_available_datasets():
    """
    Print information about all available datasets.
    """
    print(f"\n{'='*80}")
    print(f"Available Real-World Datasets")
    print(f"{'='*80}")
    
    datasets = list_available_datasets()
    
    # Group by source
    by_source = {}
    for dataset_id, info in datasets.items():
        source = info['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append((dataset_id, info))
    
    # Print by source
    for source, dataset_list in by_source.items():
        print(f"\n{source} Datasets:")
        print(f"{'-'*60}")
        
        for dataset_id, info in dataset_list:
            nodes = info.get('nodes', 'Unknown')
            edges = info.get('edges', 'Unknown')
            print(f"- {dataset_id}: {info['description']}")
            if nodes != 'Unknown' and edges != 'Unknown':
                print(f"  ({nodes:,} nodes, {edges:,} edges)")
        
    print("\nTo use a dataset, call load_dataset('dataset-name') or load_dataset_as_networkx('dataset-name')")


def analyze_dataset(dataset_name, sample_size=None, dim=3, num_iterations=30):
    """
    Download, load, and analyze a dataset.
    
    Parameters:
        dataset_name: str
            Name of the dataset to analyze
        sample_size: int, optional
            If set, sample the graph to this number of nodes for visualization
        dim: int
            Dimension of the embedding
        num_iterations: int
            Number of layout iterations
    """
    print(f"\n{'='*80}")
    print(f"Analyzing dataset: {dataset_name}")
    print(f"{'='*80}")
    
    # Load the dataset
    print(f"Loading dataset {dataset_name}...")
    start_time = time.time()
    edges, n_vertices = load_dataset(dataset_name)
    load_time = time.time() - start_time
    
    print(f"Loaded dataset with {n_vertices:,} vertices and {len(edges):,} edges in {load_time:.2f}s")
    
    # Sample the graph if needed
    if sample_size is not None and sample_size < n_vertices:
        print(f"Sampling {sample_size:,} vertices from the graph...")
        sampled_vertices = np.random.choice(n_vertices, sample_size, replace=False)
        vertex_map = {old_idx: new_idx for new_idx, old_idx in enumerate(sampled_vertices)}
        
        # Filter edges that contain sampled vertices
        sampled_edges = []
        for u, v in edges:
            if u in vertex_map and v in vertex_map:
                sampled_edges.append((vertex_map[u], vertex_map[v]))
        
        edges = np.array(sampled_edges)
        n_vertices = sample_size
        
        print(f"Sampled graph has {n_vertices:,} vertices and {len(edges):,} edges")
    
    # Create NetworkX graph for analysis
    G = nx.Graph()
    G.add_nodes_from(range(n_vertices))
    G.add_edges_from(edges)
    
    # Analyze graph properties
    density = 2 * len(edges) / (n_vertices * (n_vertices - 1))
    avg_degree = 2 * len(edges) / n_vertices
    
    print(f"Graph statistics:")
    print(f"- Density: {density:.6f}")
    print(f"- Average degree: {avg_degree:.2f}")
    
    # Measure connected components
    components = list(nx.connected_components(G))
    print(f"- Number of connected components: {len(components):,}")
    print(f"- Largest component size: {len(max(components, key=len)):,} vertices")
    
    # Analyze largest connected component
    largest_cc = max(components, key=len)
    if len(largest_cc) < n_vertices:
        print(f"Extracting largest connected component with {len(largest_cc):,} vertices...")
        G_cc = G.subgraph(largest_cc).copy()
        
        # Re-index nodes to be consecutive integers
        G_cc = nx.convert_node_labels_to_integers(G_cc)
        
        # Extract edges from the largest component
        edges = np.array(list(G_cc.edges()))
        n_vertices = len(largest_cc)
    
    # Compute diameter if manageable
    if n_vertices < 10000:
        try:
            diameter = nx.diameter(G)
            print(f"- Diameter: {diameter}")
        except nx.NetworkXError:
            print("- Diameter: N/A (Graph not connected)")
    else:
        print("- Diameter: Skipped (Graph too large)")
    
    # Compute average shortest path length if manageable
    if n_vertices < 10000:
        try:
            avg_path_length = nx.average_shortest_path_length(G)
            print(f"- Average shortest path length: {avg_path_length:.2f}")
        except nx.NetworkXError:
            print("- Average shortest path length: N/A (Graph not connected)")
    else:
        print("- Average shortest path length: Skipped (Graph too large)")
    
    # Compute clustering coefficient
    avg_clustering = nx.average_clustering(G)
    print(f"- Average clustering coefficient: {avg_clustering:.4f}")
    
    # Create and run embedder
    print(f"Creating embedder with dimension {dim}...")
    embedder = GraphEmbedder(
        edges=edges,
        n_vertices=n_vertices,
        dimension=dim,
        L_min=10.0,
        k_attr=0.5,
        k_inter=0.1,
        knn_k=min(15, n_vertices // 10),
        sample_size=min(512, len(edges)),
        batch_size=min(1024, n_vertices),
        verbose=True
    )
    
    print(f"Running layout for {num_iterations} iterations...")
    layout_start = time.time()
    embedder.run_layout(num_iterations=num_iterations)
    layout_time = time.time() - layout_start
    print(f"Layout completed in {layout_time:.2f}s")
    
    # Calculate centrality measures
    print("Calculating centrality measures...")
    
    # Get positions and calculate radial distances
    positions = np.array(embedder.positions)
    radii = np.linalg.norm(positions, axis=1)
    
    # Calculate centrality measures
    degree = np.array([d for _, d in G.degree()])
    
    # Only calculate betweenness for smaller graphs
    if n_vertices < 5000:
        print("Calculating betweenness centrality...")
        betweenness = np.array(list(nx.betweenness_centrality(G).values()))
    else:
        print("Skipping betweenness centrality (graph too large)")
        betweenness = np.zeros(n_vertices)
    
    print("Calculating eigenvector centrality...")
    try:
        eigenvector = np.array(list(nx.eigenvector_centrality_numpy(G).values()))
    except:
        print("Error calculating eigenvector centrality, using zeros")
        eigenvector = np.zeros(n_vertices)
    
    print("Calculating PageRank...")
    pagerank = np.array(list(nx.pagerank(G).values()))
    
    print("Calculating closeness centrality...")
    if n_vertices < 5000:
        closeness = np.array(list(nx.closeness_centrality(G).values()))
    else:
        print("Skipping closeness centrality (graph too large)")
        closeness = np.zeros(n_vertices)
    
    # Display correlation with radial distances
    print("\nCorrelation between embedding radii and centrality measures:")
    report_full_correlation_matrix(
        radii, 
        degree,
        betweenness,
        eigenvector,
        pagerank,
        closeness,
        np.zeros_like(radii)  # placeholder for edge betweenness
    )
    
    # Display the graph
    print("Displaying graph layout...")
    embedder.display_layout(edge_width=0.5, node_size=5)
    
    # Color nodes by degree centrality
    print("Displaying graph layout with nodes colored by degree centrality...")
    normalized_degree = (degree - np.min(degree)) / (np.max(degree) - np.min(degree) + 1e-10)
    embedder.display_layout(edge_width=0.5, node_size=5, node_colors=normalized_degree)
    
    return embedder, G


def compare_datasets(dataset_names, sample_size=1000, dim=3, num_iterations=30):
    """
    Compare multiple datasets by analyzing their properties.
    
    Parameters:
        dataset_names: list
            List of dataset names to compare
        sample_size: int
            Sample size for each dataset
        dim: int
            Dimension of the embedding
        num_iterations: int
            Number of layout iterations
    """
    print(f"\n{'='*80}")
    print(f"Comparing Multiple Datasets")
    print(f"{'='*80}")
    
    results = []
    
    for dataset_name in dataset_names:
        print(f"\n{'-'*60}")
        print(f"Dataset: {dataset_name}")
        print(f"{'-'*60}")
        
        # Load the dataset
        print(f"Loading dataset {dataset_name}...")
        start_time = time.time()
        edges, n_vertices = load_dataset(dataset_name)
        load_time = time.time() - start_time
        
        print(f"Loaded dataset with {n_vertices:,} vertices and {len(edges):,} edges in {load_time:.2f}s")
        
        # Sample the graph
        print(f"Sampling {sample_size:,} vertices from the graph...")
        sampled_vertices = np.random.choice(n_vertices, sample_size, replace=False)
        vertex_map = {old_idx: new_idx for new_idx, old_idx in enumerate(sampled_vertices)}
        
        # Filter edges that contain sampled vertices
        sampled_edges = []
        for u, v in edges:
            if u in vertex_map and v in vertex_map:
                sampled_edges.append((vertex_map[u], vertex_map[v]))
        
        edges = np.array(sampled_edges)
        n_vertices = sample_size
        
        print(f"Sampled graph has {n_vertices:,} vertices and {len(edges):,} edges")
        
        # Create NetworkX graph for analysis
        G = nx.Graph()
        G.add_nodes_from(range(n_vertices))
        G.add_edges_from(edges)
        
        # Analyze graph properties
        density = 2 * len(edges) / (n_vertices * (n_vertices - 1))
        avg_degree = 2 * len(edges) / n_vertices
        
        # Get largest connected component
        largest_cc = max(nx.connected_components(G), key=len)
        lcc_size = len(largest_cc)
        lcc_fraction = lcc_size / n_vertices
        
        # Compute average shortest path length if manageable
        try:
            diameter = nx.diameter(G)
        except nx.NetworkXError:
            diameter = float('nan')
        
        try:
            avg_path_length = nx.average_shortest_path_length(G)
        except nx.NetworkXError:
            avg_path_length = float('nan')
        
        # Compute clustering coefficient
        avg_clustering = nx.average_clustering(G)
        
        # Create and run embedder
        embedder = GraphEmbedder(
            edges=edges,
            n_vertices=n_vertices,
            dimension=dim,
            L_min=10.0,
            k_attr=0.5,
            k_inter=0.1,
            knn_k=min(15, n_vertices // 10),
            sample_size=min(512, len(edges)),
            batch_size=min(1024, n_vertices),
            verbose=False
        )
        
        layout_start = time.time()
        embedder.run_layout(num_iterations=num_iterations)
        layout_time = time.time() - layout_start
        
        # Get positions and calculate radial distances
        positions = np.array(embedder.positions)
        radii = np.linalg.norm(positions, axis=1)
        
        # Calculate centrality measures
        degree = np.array([d for _, d in G.degree()])
        
        # Store results
        results.append({
            'dataset': dataset_name,
            'vertices': n_vertices,
            'edges': len(edges),
            'density': density,
            'avg_degree': avg_degree,
            'lcc_size': lcc_size,
            'lcc_fraction': lcc_fraction,
            'diameter': diameter,
            'avg_path_length': avg_path_length,
            'avg_clustering': avg_clustering,
            'layout_time': layout_time
        })
    
    # Create comparison table
    df = pd.DataFrame(results)
    
    print("\nDataset Comparison Results:")
    print(df)
    
    # Create visualizations
    # Plot layout time vs edges
    fig = px.scatter(
        df, x='edges', y='layout_time', 
        hover_data=['dataset', 'vertices', 'avg_degree'],
        title='Layout Time vs. Number of Edges',
        labels={'edges': 'Number of Edges', 'layout_time': 'Layout Time (seconds)'}
    )
    fig.show()
    
    # Plot clustering coefficient vs average degree
    fig = px.scatter(
        df, x='avg_degree', y='avg_clustering', 
        hover_data=['dataset', 'vertices', 'edges'],
        title='Clustering Coefficient vs. Average Degree',
        labels={'avg_degree': 'Average Degree', 'avg_clustering': 'Average Clustering Coefficient'}
    )
    fig.show()
    
    return df


def main():
    """
    Main function to demonstrate working with real-world datasets.
    """
    # Print available datasets
    print_available_datasets()
    
    # Analyze a small social network dataset
    analyze_dataset('snap-facebook_combined', dim=3, num_iterations=50)
    
    # Analyze a medium-sized dataset with sampling
    analyze_dataset('snap-ca-GrQc', sample_size=1000, dim=3, num_iterations=30)
    
    # Compare multiple datasets
    compare_datasets([
        'snap-facebook_combined',
        'snap-ca-GrQc',
        'snap-ca-HepTh',
        'snap-wiki-vote'
    ], sample_size=500, dim=3, num_iterations=20)


if __name__ == "__main__":
    main()
