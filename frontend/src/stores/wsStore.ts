import { create } from 'zustand';

export interface LiveWSEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  payload: any;
}

interface WSState {
  isConnected: boolean;
  isConnecting: boolean;
  recentEvents: LiveWSEvent[];
  addEvent: (event: LiveWSEvent) => void;
  setConnected: (status: boolean) => void;
  setConnecting: (status: boolean) => void;
}

export const useWSStore = create<WSState>((set) => ({
  isConnected: false,
  isConnecting: false,
  recentEvents: [],

  addEvent: (event) =>
    set((state) => ({
      recentEvents: [event, ...state.recentEvents].slice(0, 50),
    })),

  setConnected: (status) => set({ isConnected: status }),
  setConnecting: (status) => set({ isConnecting: status }),
}));
