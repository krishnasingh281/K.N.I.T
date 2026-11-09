export const clusterState = {
  nodes: {},
  assignments: {},
  isGenerating: false, // NEW: Tracks if the cluster is actively processing a prompt
};