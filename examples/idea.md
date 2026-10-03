# Adaptive Code Review Risk Router

## Problem
Engineering teams waste reviewer time because pull requests are routed using static ownership rules that miss implementation risk.

## Mechanism
The system builds a typed dependency graph from changed files, runtime incidents, code owners, and test coverage, then routes review requests based on graph paths affected by the change.

## Data Flow
A pull request event enters an ingestion queue, changed files are mapped to graph nodes, incident and coverage signals update edge weights, and a ranked reviewer plan is written back to the code hosting system.

## Algorithm
For each changed node, the algorithm performs bounded graph expansion, applies decayed incident weights and coverage penalties, computes reviewer expertise scores, and selects a minimal reviewer set that covers high-risk paths.

## Technical Novelty
Graph edge weights are updated from production incident proximity and test coverage deltas so the routing decision reflects current runtime risk instead of static ownership alone.

## Implementation Notes
The implementation uses a persistent graph index, webhook ingestion, and incremental recomputation to keep latency below two seconds for typical pull requests.
