import { configureStore } from "@reduxjs/toolkit";
// 1. Import the default export (the reducer) from your new slice
import clusterReducer from "../features/dashboard/dashboardSlice.js";

export const store = configureStore({
  reducer: {
    // 2. Register the slice under the state key 'cluster'
    cluster: clusterReducer,
  },
});