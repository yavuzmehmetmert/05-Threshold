import { create } from 'zustand';

interface AnalyticsState {
    pmcData: { date: string; ctl: number; atl: number; tsb: number }[];
    acwr: number;
    rampRate: number;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
    pmcData: [
        { date: '2023-11-01', ctl: 40, atl: 35, tsb: 5 },
        { date: '2023-11-08', ctl: 42, atl: 45, tsb: -3 },
        { date: '2023-11-15', ctl: 45, atl: 55, tsb: -10 },
        { date: '2023-11-22', ctl: 48, atl: 60, tsb: -12 },
        { date: '2023-11-29', ctl: 50, atl: 40, tsb: 10 },
        { date: '2023-12-05', ctl: 52, atl: 30, tsb: 22 },
    ],
    acwr: 1.2,
    rampRate: 15, // %
}));
