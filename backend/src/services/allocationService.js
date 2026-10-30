/**
 * Triggers whenever the cluster topology changes.
 * Calculates layer boundaries based on VRAM capacity and broadcasts to workers.
 */
export const recalculatePipeline = (clusterState, io) => {
  console.log("\n🔄 [Allocation Service] Cluster topology changed! Recalculating pipeline...");

  // 1. Filter out dead nodes
  const activeNodes = Object.values(clusterState.nodes).filter(
    (node) => node.status === "active"
  );

  const nodeCount = activeNodes.length;

  if (nodeCount === 0) {
    console.log("⚠️ No active nodes available to process layers. Cluster empty.");
    return {};
  }

  // 2. Deterministic Sorting: Sort by the time they joined to maintain pipeline order
  activeNodes.sort((a, b) => a.joinedAt - b.joinedAt);

  // 3. Hardware-Aware Math: Calculate total cluster VRAM
  const TOTAL_LAYERS = 80; 
  
  // Extract the numeric VRAM value (e.g., "24GB" -> 24). Default to 8 if parsing fails.
  const nodesWithCapacity = activeNodes.map(node => {
    const vramNum = parseInt(node.vram.replace(/\D/g, '')) || 8; 
    return { ...node, vramNum };
  });

  const totalVram = nodesWithCapacity.reduce((sum, node) => sum + node.vramNum, 0);

  // 4. Proportional Distribution
  let totalAssignedSoFar = 0;
  
  // Step A: Give everyone their guaranteed baseline layers based on their VRAM percentage
  nodesWithCapacity.forEach(node => {
    const proportion = node.vramNum / totalVram;
    const exactLayers = TOTAL_LAYERS * proportion;
    
    node.baseLayers = Math.floor(exactLayers); // The guaranteed whole number of layers
    node.remainderFraction = exactLayers - node.baseLayers; // The decimal leftover
    totalAssignedSoFar += node.baseLayers;
  });

  // Step B: Largest Remainder Method for the leftover layers
  let leftoverLayers = TOTAL_LAYERS - totalAssignedSoFar;
  
  // Sort a temporary array by who got shortchanged the most by the Math.floor() rounding
  const remainderQueue = [...nodesWithCapacity].sort((a, b) => b.remainderFraction - a.remainderFraction);

  // Hand out the leftovers one by one
  for (let i = 0; i < leftoverLayers; i++) {
    remainderQueue[i].baseLayers += 1;
  }

  // 5. Build the final Assignment Object
  let currentStart = 0;
  const assignments = {};

  for (let i = 0; i < nodesWithCapacity.length; i++) {
    const currentNode = nodesWithCapacity[i];
    const layersForThisNode = currentNode.baseLayers;

    const endLayer = currentStart + layersForThisNode - 1;
    const nextNodeId = i < nodesWithCapacity.length - 1 ? nodesWithCapacity[i + 1].id : null;

    assignments[currentNode.id] = {
      orderIndex: i + 1, 
      startLayer: currentStart,
      endLayer: layersForThisNode > 0 ? endLayer : currentStart - 1,
      totalAssigned: layersForThisNode,
      nextNode: nextNodeId,
    };

    currentStart += layersForThisNode; // Shift the start index for the next machine
  }

  console.log("📊 Hardware-Aware Pipeline Assignments:", assignments);

  return assignments;
};