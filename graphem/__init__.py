"""
Graphem: A graph embedding library based on JAX for efficient k-nearest neighbors.
"""

from graphem.embedder import GraphEmbedder
from graphem.index import HPIndex
from graphem.influence import graphem_seed_selection, ndlib_estimated_influence, greedy_seed_selection
from graphem.datasets import load_dataset
from graphem.generators import (
    erdos_renyi_graph,
    generate_ba,
    generate_ws,
    generate_random_regular,
    generate_sbm,
    generate_scale_free,
    generate_geometric,
    generate_caveman,
    generate_relaxed_caveman
)
from graphem.visualization import (
    report_corr, 
    report_full_correlation_matrix, 
    plot_radial_vs_centrality, 
    display_benchmark_results
)

# Add aliases for backward compatibility and to fix pylint warnings
generate_erdos_renyi_graph = erdos_renyi_graph
generate_barabasi_albert_graph = generate_ba
generate_watts_strogatz_graph = generate_ws
generate_random_regular_graph = generate_random_regular
generate_sbm_graph = generate_sbm
generate_scale_free_graph = generate_scale_free
generate_geometric_graph = generate_geometric
generate_caveman_graph = generate_caveman
generate_relaxed_caveman_graph = generate_relaxed_caveman
visualize_graph = plot_radial_vs_centrality  # This was likely the intended alias

__version__ = '0.1.0'
