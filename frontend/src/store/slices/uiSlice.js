import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  theme: 'dark',
  sidebarOpen: true,
  notifications: [],
  loadingStates: {},
  modalStack: [],
  drawerOpen: false,
  snackbar: {
    open: false,
    message: '',
    severity: 'info',
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action) => {
      state.theme = action.payload;
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action) => {
      state.sidebarOpen = action.payload;
    },
    addNotification: (state, action) => {
      state.notifications.push({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        ...action.payload,
      });
    },
    removeNotification: (state, action) => {
      state.notifications = state.notifications.filter(
        notification => notification.id !== action.payload
      );
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },
    setLoadingState: (state, action) => {
      const { key, loading } = action.payload;
      state.loadingStates[key] = loading;
    },
    pushModal: (state, action) => {
      state.modalStack.push(action.payload);
    },
    popModal: (state) => {
      state.modalStack.pop();
    },
    clearModals: (state) => {
      state.modalStack = [];
    },
    setDrawerOpen: (state, action) => {
      state.drawerOpen = action.payload;
    },
    showSnackbar: (state, action) => {
      state.snackbar = {
        open: true,
        ...action.payload,
      };
    },
    hideSnackbar: (state) => {
      state.snackbar.open = false;
    },
    setFullscreen: (state, action) => {
      state.isFullscreen = action.payload;
    },
    setWindowSize: (state, action) => {
      state.windowSize = action.payload;
    },
  },
});

export const {
  setTheme,
  toggleSidebar,
  setSidebarOpen,
  addNotification,
  removeNotification,
  clearNotifications,
  setLoadingState,
  pushModal,
  popModal,
  clearModals,
  setDrawerOpen,
  showSnackbar,
  hideSnackbar,
  setFullscreen,
  setWindowSize,
} = uiSlice.actions;

export default uiSlice.reducer;