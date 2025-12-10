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
    activities: [
        {
            activityId: 21211964840,
            activityName: 'Maltepe Koşu',
            startTimeLocal: '2025-12-09 17:54:23',
            activityType: 'running',
            distance: 10029.8,
            duration: 3678.56,
            averageHeartRate: 153,
            calories: 664,
            elevationGain: 0,
            avgSpeed: 2.73
        },
        {
            activityId: 21191147529,
            activityName: 'Paris Koşu',
            startTimeLocal: '2025-12-07 09:12:18',
            activityType: 'running',
            distance: 15020.31,
            duration: 6037.06,
            averageHeartRate: 139,
            calories: 981,
            elevationGain: 0,
            avgSpeed: 2.49
        },
        {
            activityId: 21168464433,
            activityName: 'Maltepe Koşu',
            startTimeLocal: '2025-12-04 17:55:09',
            activityType: 'running',
            distance: 10025.21,
            duration: 3737.67,
            averageHeartRate: 157,
            calories: 682,
            elevationGain: 0,
            avgSpeed: 2.68
        },
        {
            activityId: 21159728483,
            activityName: 'Maltepe Koşu',
            startTimeLocal: '2025-12-03 17:53:39',
            activityType: 'running',
            distance: 15016.30,
            duration: 4985.98,
            averageHeartRate: 165,
            calories: 983,
            elevationGain: 0,
            avgSpeed: 3.01
        },
        {
            activityId: 21149961122,
            activityName: 'Maltepe Koşu',
            startTimeLocal: '2025-12-02 17:43:10',
            activityType: 'running',
            distance: 10017.73,
            duration: 3743.22,
            averageHeartRate: 154,
            calories: 669,
            elevationGain: 0,
            avgSpeed: 2.68
        },
        {
            activityId: 21127956904,
            activityName: 'Kadıköy Koşu',
            startTimeLocal: '2025-11-30 09:04:38',
            activityType: 'running',
            distance: 15031.38,
            duration: 5255.10,
            averageHeartRate: 158,
            calories: 1001,
            elevationGain: 0,
            avgSpeed: 2.86
        },
        {
            activityId: 21119090141,
            activityName: 'Kadıköy Koşu',
            startTimeLocal: '2025-11-29 07:58:28',
            activityType: 'running',
            distance: 15026.76,
            duration: 5742.57,
            averageHeartRate: 150,
            calories: 994,
            elevationGain: 0,
            avgSpeed: 2.62
        },
        {
            activityId: 21106315226,
            activityName: 'Maltepe Koşu',
            startTimeLocal: '2025-11-27 17:34:21',
            activityType: 'running',
            distance: 10025.30,
            duration: 3605.29,
            averageHeartRate: 160,
            calories: 687,
            elevationGain: 0,
            avgSpeed: 2.78
        },
        {
            activityId: 21087835001,
            activityName: 'Maltepe Koşu',
            startTimeLocal: '2025-11-25 17:41:59',
            activityType: 'running',
            distance: 10023.94,
            duration: 3730.03,
            averageHeartRate: 154,
            calories: 679,
            elevationGain: 0,
            avgSpeed: 2.69
        },
        {
            activityId: 21065760218,
            activityName: 'Kadıköy Koşu',
            startTimeLocal: '2025-11-23 08:25:16',
            activityType: 'running',
            distance: 15055.44,
            duration: 6000.59,
            averageHeartRate: 141,
            calories: 980,
            elevationGain: 0,
            avgSpeed: 2.51
        }
    ],

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
