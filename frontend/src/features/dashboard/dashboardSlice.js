import { createSlice, createSelector } from "@reduxjs/toolkit";

const initialState = {
  nodes: {},
  assignments: {},
};

const clusterSlice = createSlice({
  name: "cluster",
  initialState,
  reducers: {
    setNodes: (state, action) => {
      state.nodes = action.payload;
    },
    setAssignments: (state, action) => {
      state.assignments = action.payload;
    },
  },
});

export const { setNodes, setAssignments } = clusterSlice.actions;

// Step 1: Select the raw object from the state
const selectNodesObject = (state) => state.cluster.nodes;

// Step 2: Create a memoized selector that only runs when selectNodesObject changes
export const selectAllNodes = createSelector(
  [selectNodesObject],
  (nodesObject) => Object.values(nodesObject),
);

export default clusterSlice.reducer;
