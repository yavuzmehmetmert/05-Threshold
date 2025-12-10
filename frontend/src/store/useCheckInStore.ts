import { create } from 'zustand';

interface CheckInState {
    freshnessOverride: number; // -60 to +60
    sorenessScore: number; // 1 to 10
    mentalStress: number; // 1 to 5

    setFreshnessOverride: (val: number) => void;
    setSorenessScore: (val: number) => void;
    setMentalStress: (val: number) => void;
}

export const useCheckInStore = create<CheckInState>((set) => ({
    freshnessOverride: 0,
    sorenessScore: 1,
    mentalStress: 1,

    setFreshnessOverride: (freshnessOverride) => set({ freshnessOverride }),
    setSorenessScore: (sorenessScore) => set({ sorenessScore }),
    setMentalStress: (mentalStress) => set({ mentalStress }),
}));
