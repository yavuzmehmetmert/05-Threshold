import { create } from 'zustand';

interface OnboardingState {
    raceDate: string;
    raceType: 'Marathon' | 'Half Marathon' | '5K' | '';
    weeklyVolume: string;
    recentRaceTime: string;
    dailyTrainingLimit: string;
    injuryHistory: boolean;
    surfaceType: 'Road' | 'Trail' | 'Mixed' | '';
    riskTolerance: 'Low' | 'Medium' | 'High' | '';

    setRaceDate: (date: string) => void;
    setRaceType: (type: 'Marathon' | 'Half Marathon' | '5K') => void;
    setWeeklyVolume: (volume: string) => void;
    setRecentRaceTime: (time: string) => void;
    setDailyTrainingLimit: (limit: string) => void;
    setInjuryHistory: (hasHistory: boolean) => void;
    setSurfaceType: (type: 'Road' | 'Trail' | 'Mixed') => void;
    setRiskTolerance: (tolerance: 'Low' | 'Medium' | 'High') => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
    raceDate: '',
    raceType: '',
    weeklyVolume: '',
    recentRaceTime: '',
    dailyTrainingLimit: '',
    injuryHistory: false,
    surfaceType: '',
    riskTolerance: '',

    setRaceDate: (raceDate) => set({ raceDate }),
    setRaceType: (raceType) => set({ raceType }),
    setWeeklyVolume: (weeklyVolume) => set({ weeklyVolume }),
    setRecentRaceTime: (recentRaceTime) => set({ recentRaceTime }),
    setDailyTrainingLimit: (dailyTrainingLimit) => set({ dailyTrainingLimit }),
    setInjuryHistory: (injuryHistory) => set({ injuryHistory }),
    setSurfaceType: (surfaceType) => set({ surfaceType }),
    setRiskTolerance: (riskTolerance) => set({ riskTolerance }),
}));
