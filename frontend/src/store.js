import { configureStore } from '@reduxjs/toolkit';
import workflowReducer from './store/slices/workflowSlice';
import authReducer from './store/slices/authSlice';
import uiReducer from './store/slices/uiSlice';

export const store = configureStore({
  reducer: {
    workflow: workflowReducer,
    auth: authReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }),
  devTools: process.env.NODE_ENV !== 'production',
});

export default store;