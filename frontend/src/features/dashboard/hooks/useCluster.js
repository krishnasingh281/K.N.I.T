import { useEffect } from "react";
import { useDispatch } from "react-redux";
import { setNodes, setAssignments } from "../dashboardSlice.js";
import {
  subscribeToClusterUpdates,
  unsubscribeFromClusterUpdates,
  subscribeToPipelineUpdates, 
  unsubscribeFromPipelineUpdates, 
} from "../services/dashboard.service.js";

export const useCluster = () => {
  const dispatch = useDispatch();

  useEffect(() => {
    subscribeToClusterUpdates((data) => {
      dispatch(setNodes(data));
    });

    // <-- NEW: Listen for the math and save it to Redux
    subscribeToPipelineUpdates((data) => {
      dispatch(setAssignments(data));
    });

    return () => {
      unsubscribeFromClusterUpdates();
      unsubscribeFromPipelineUpdates(); // <-- NEW: Cleanup
    };
  }, [dispatch]);

  return {};
};
