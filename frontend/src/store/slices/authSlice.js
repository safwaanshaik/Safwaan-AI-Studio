import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  permissions: [],
  profile: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    loginSuccess: (state, action) => {
      state.isLoading = false;
      state.isAuthenticated = true;
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.permissions = action.payload.permissions || [];
      state.profile = action.payload.profile;
      state.error = null;
    },
    loginFailure: (state, action) => {
      state.isLoading = false;
      state.isAuthenticated = false;
      state.user = null;
      state.token = null;
      state.permissions = [];
      state.profile = null;
      state.error = action.payload;
    },
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.permissions = [];
      state.profile = null;
      state.error = null;
    },
    updateProfile: (state, action) => {
      state.profile = { ...state.profile, ...action.payload };
      if (state.user) {
        state.user = { ...state.user, ...action.payload };
      }
    },
    updatePermissions: (state, action) => {
      state.permissions = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    refreshToken: (state, action) => {
      state.token = action.payload.token;
    },
  },
});

export const {
  loginStart,
  loginSuccess,
  loginFailure,
  logout,
  updateProfile,
  updatePermissions,
  clearError,
  refreshToken,
} = authSlice.actions;

export default authSlice.reducer;