import { create } from 'zustand';

interface DashboardState {
    readinessScore: number; // 0-100
    tsb: number; // Form
    bodyBattery: number; // 0-100
    todayWorkout: {
        type: string;
        duration: string;
        intensity: string;
        description: string;
    } | null;
    adaptation: {
        active: boolean;
        reason: string;
        change: string;
    } | null;
    // Onboarding State
    isOnboarded: boolean;
    userProfile: {
        name: string;
        email: string;
        maxHr: number;
        restingHr: number;
        lthr: number;
        hrZones?: number[]; // [Z1_floor, Z2_floor, Z3_floor, Z4_floor, Z5_floor]
        vo2max: number;
        weight: number;
        stressScore: number;
    };
    goals: {
        targetRace: string;
        trainingDays: string[]; // e.g., ['Mon', 'Wed', 'Sat']
        longRunDay: string;     // e.g., 'Sat'
        experienceLevel: string;
    };
    weeklyHours: number;
    gear: {
        shoes: Array<{ id: string; name: string; mileage: number; maxMileage: number }>;
        devices: Array<{ id: string; name: string; type: string }>;
    };
    activities: Array<{
        activityId: number;
        activityName: string;
        startTimeLocal: string;
        activityType: string;
        distance: number;
        duration: number;
        averageHeartRate: number;
        calories: number;
        elevationGain: number;
        avgSpeed: number;
        weather?: {
            temp: number;      // Celsius
            humidity: number;  // %
            windSpeed: number; // km/h
            aqi: number;       // 0-500
            condition: string; // 'Sunny', 'Cloudy', 'Rainy'
        };
    }>;

    // Actions
    setReadinessScore: (val: number) => void;
    setBodyBattery: (val: number) => void;
    setTsb: (val: number) => void;
    setOnboarded: (status: boolean) => void;
    updateUserProfile: (data: Partial<DashboardState['userProfile']>) => void;
    setGoals: (goals: Partial<DashboardState['goals']>) => void;
    addShoe: (shoe: { name: string; mileage: number }) => void;
    addDevice: (device: { name: string; type: string }) => void;
    setActivities: (activities: DashboardState['activities']) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
    readinessScore: 85,
    tsb: 12,
    bodyBattery: 72,
    todayWorkout: {
        type: 'Threshold Run',
        duration: '45 min',
        intensity: 'Zone 4',
        description: '3x8 min @ Threshold Pace w/ 2 min recovery',
    },
    adaptation: {
        active: false,
        reason: 'Low HRV detected (-22%)',
        change: 'Intervals converted to Zone 2 Recovery Run',
    },

    setReadinessScore: (readinessScore) => set({ readinessScore }),

    // Initial State for Onboarding
    isOnboarded: true, // MOCK MODE ENABLED
    userProfile: {
        name: '',
        email: '',
        maxHr: 190,
        restingHr: 50,
        lthr: 170,
        vo2max: 50,
        weight: 70,
        stressScore: 25,
    },
    goals: {
        targetRace: '',
        trainingDays: [],
        longRunDay: '',
        experienceLevel: 'Intermediate',
    },
    weeklyHours: 5,
    gear: {
        shoes: [],
        devices: [],
    },
    // MOCK DATA - Gerçek Garmin verileri
    activities: [],

    // Actions Implementation
    setBodyBattery: (val) => set({ bodyBattery: val }),
    setTsb: (val) => set({ tsb: val }),
    setOnboarded: (status) => set({ isOnboarded: status }),
    updateUserProfile: (data) => set((state) => ({ userProfile: { ...state.userProfile, ...data } })),
    setGoals: (data) => set((state) => ({ goals: { ...state.goals, ...data } })),
    setActivities: (activities) => set({ activities }),
    addShoe: (shoe) => set((state) => ({
        gear: {
            ...state.gear,
            shoes: [
                ...state.gear.shoes,
                { id: Math.random().toString(), maxMileage: 800, ...shoe }
            ]
        }
    })),
    addDevice: (device) => set((state) => ({
        gear: {
            ...state.gear,
            devices: [
                ...state.gear.devices,
                { id: Math.random().toString(), ...device }
            ]
        }
    })),
}));
