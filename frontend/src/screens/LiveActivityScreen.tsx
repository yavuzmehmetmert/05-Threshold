import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Dimensions, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { Play, Pause, Square } from 'lucide-react-native';
import Animated, { useSharedValue, useAnimatedStyle, withSpring, withRepeat, withTiming, interpolateColor, useDerivedValue } from 'react-native-reanimated';

const { width, height } = Dimensions.get('window');

type DashboardMode = 'HIIT' | 'ENDURANCE' | 'RECOVERY';

export default function LiveActivityScreen() {
    const navigation = useNavigation();
    const [mode, setMode] = useState<DashboardMode>('HIIT'); // Default to HIIT for demo
    const [isRunning, setIsRunning] = useState(false);
    const [elapsed, setElapsed] = useState(0);

    // Simulation Data
    const [hr, setHr] = useState(140);
    const [pace, setPace] = useState(300); // 5:00/km in sec
    const [cadence, setCadence] = useState(170);

    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isRunning) {
            interval = setInterval(() => {
                setElapsed(e => e + 1);
                // Simulate data fluctuation
                setHr(h => Math.min(195, Math.max(130, h + (Math.random() - 0.5) * 5)));
                setCadence(c => Math.min(190, Math.max(160, c + (Math.random() - 0.5) * 2)));
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [isRunning]);

    const formatTime = (sec: number) => {
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    };

    return (
        <SafeAreaView style={styles.container}>
            {/* Context Switcher (For Demo) */}
            <View style={styles.switcher}>
                {(['HIIT', 'ENDURANCE', 'RECOVERY'] as DashboardMode[]).map(m => (
                    <TouchableOpacity key={m} onPress={() => setMode(m)} style={[styles.switchBtn, mode === m && styles.switchBtnActive]}>
                        <Text style={[styles.switchText, mode === m && styles.switchTextActive]}>{m}</Text>
                    </TouchableOpacity>
                ))}
            </View>

            {/* Content Area ("The Wipe") */}
            <View style={styles.content}>
                {mode === 'HIIT' && <HIITView hr={hr} elapsed={elapsed} />}
                {mode === 'ENDURANCE' && <EnduranceView hr={hr} pace={pace} />}
                {mode === 'RECOVERY' && <RecoveryView cadence={cadence} />}
            </View>

            {/* Controls */}
            <View style={styles.controls}>
                <TouchableOpacity onPress={() => setIsRunning(!isRunning)} style={styles.controlBtn}>
                    {isRunning ? <Pause color="black" size={32} /> : <Play color="black" size={32} />}
                </TouchableOpacity>
                <TouchableOpacity onPress={() => navigation.goBack()} style={[styles.controlBtn, { backgroundColor: '#FF3333' }]}>
                    <Square color="black" size={32} />
                </TouchableOpacity>
            </View>
        </SafeAreaView>
    );
}

// --------------------------------------------------------------------------------
// SCENARIO A: HIIT (Hypofrontality)
// --------------------------------------------------------------------------------
const HIITView = ({ hr, elapsed }: { hr: number, elapsed: number }) => {
    // Pulse Animation for High Intensity
    const pulse = useSharedValue(1);

    useEffect(() => {
        if (hr > 170) {
            pulse.value = withRepeat(withTiming(1.1, { duration: 500 }), -1, true);
        } else {
            pulse.value = withTiming(1);
        }
    }, [hr]);

    const animatedStyle = useAnimatedStyle(() => ({
        transform: [{ scale: pulse.value }],
    }));

    const zoneColor = hr > 170 ? '#FF3333' : hr > 150 ? '#FFCC00' : '#33FF33';

    return (
        <View style={[styles.modeContainer, { backgroundColor: '#000' }]}>
            <Animated.View style={[styles.bigCircle, { backgroundColor: zoneColor }, animatedStyle]}>
                <Text style={styles.giantTimer}>{Math.floor(elapsed / 60)}:{(elapsed % 60).toString().padStart(2, '0')}</Text>
                <Text style={styles.zoneLabel}>{hr > 170 ? 'ZONE 5' : hr > 150 ? 'ZONE 4' : 'ZONE 3'}</Text>
            </Animated.View>
        </View>
    );
};

// --------------------------------------------------------------------------------
// SCENARIO B: ENDURANCE (Efficiency)
// --------------------------------------------------------------------------------
const EnduranceView = ({ hr, pace }: { hr: number, pace: number }) => {
    return (
        <View style={styles.modeContainer}>
            <Text style={styles.modeTitle}>EFFICIENCY MONITOR</Text>

            {/* Rolling Pace */}
            <View style={styles.row}>
                <Text style={styles.label}>Rolling Pace</Text>
                <Text style={styles.valueBig}>4:55</Text>
            </View>

            {/* HR Drift Monitor */}
            <View style={styles.driftContainer}>
                <View style={styles.driftBar}>
                    <View style={{ height: 100, width: 20, backgroundColor: '#3399FF', borderRadius: 4 }} />
                    <Text style={{ color: '#3399FF', marginTop: 8 }}>Pace</Text>
                </View>
                <View style={styles.driftGap}>
                    <Text style={{ color: '#888' }}>Gap: {((hr / pace) * 10).toFixed(1)}%</Text>
                </View>
                <View style={styles.driftBar}>
                    <View style={{ height: (hr / 200) * 120, width: 20, backgroundColor: '#FF3333', borderRadius: 4 }} />
                    <Text style={{ color: '#FF3333', marginTop: 8 }}>HR</Text>
                </View>
            </View>

            {/* Form Skeleton Placeholder */}
            <View style={[styles.skeletonBox, { borderColor: '#33FF33' }]}>
                <Text style={{ color: '#33FF33', fontSize: 18, fontWeight: 'bold' }}>FORM: GOOD</Text>
                <Text style={{ color: '#888', fontSize: 12 }}>GCT: 240ms</Text>
            </View>
        </View>
    );
};

// --------------------------------------------------------------------------------
// SCENARIO C: RECOVERY (Mechanics)
// --------------------------------------------------------------------------------
const RecoveryView = ({ cadence }: { cadence: number }) => {
    // Spring Animation
    const springVal = useSharedValue(0);

    useEffect(() => {
        // Bounce on every beat (simulated)
        springVal.value = withRepeat(withSpring(1, { damping: 2, stiffness: 80 }), -1, true);
    }, []);

    const springStyle = useAnimatedStyle(() => ({
        transform: [{ translateY: springVal.value * 50 }],
        height: 100 - (springVal.value * 20)
    }));

    return (
        <View style={styles.modeContainer}>
            <Text style={styles.modeTitle}>FORM DRILL</Text>

            <View style={styles.springContainer}>
                <Animated.View style={[styles.spring, springStyle]} />
                <View style={styles.ground} />
            </View>

            <View style={styles.metricRow}>
                <Text style={{ color: '#CCFF00', fontSize: 40, fontWeight: 'bold' }}>{cadence}</Text>
                <Text style={{ color: '#888', fontSize: 14 }}>SPM</Text>
            </View>
            <Text style={{ color: '#fff', textAlign: 'center', marginTop: 10 }}>Keep the spring stiff!</Text>
        </View>
    );
};

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#050505' },
    switcher: { flexDirection: 'row', justifyContent: 'space-around', padding: 10, backgroundColor: '#111' },
    switchBtn: { padding: 8, borderRadius: 8 },
    switchBtnActive: { backgroundColor: '#333' },
    switchText: { color: '#666', fontSize: 12 },
    switchTextActive: { color: '#CCFF00', fontWeight: 'bold' },
    content: { flex: 1, justifyContent: 'center', alignItems: 'center' },
    controls: { flexDirection: 'row', justifyContent: 'center', gap: 40, paddingBottom: 40 },
    controlBtn: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#CCFF00', justifyContent: 'center', alignItems: 'center' },

    // Mode Styles
    modeContainer: { flex: 1, width: '100%', justifyContent: 'center', alignItems: 'center', padding: 20 },
    bigCircle: { width: 300, height: 300, borderRadius: 150, justifyContent: 'center', alignItems: 'center' },
    giantTimer: { fontSize: 80, fontWeight: 'bold', color: '#000', fontFamily: 'System' },
    zoneLabel: { fontSize: 24, fontWeight: '900', color: '#000', marginTop: -10 },

    modeTitle: { color: '#fff', fontSize: 24, fontWeight: 'bold', marginBottom: 40 },
    row: { flexDirection: 'row', alignItems: 'baseline', gap: 10, marginBottom: 40 },
    label: { color: '#888', fontSize: 18 },
    valueBig: { color: '#fff', fontSize: 60, fontWeight: 'bold' },

    driftContainer: { flexDirection: 'row', alignItems: 'flex-end', height: 200, gap: 40, marginBottom: 40 },
    driftBar: { alignItems: 'center', justifyContent: 'flex-end', height: '100%' },
    driftGap: { height: 100, justifyContent: 'center' },

    skeletonBox: { padding: 20, borderWidth: 2, borderRadius: 12, alignItems: 'center' },

    springContainer: { height: 300, justifyContent: 'flex-end', alignItems: 'center', marginBottom: 40 },
    spring: { width: 40, backgroundColor: '#CCFF00', borderRadius: 20 },
    ground: { width: 200, height: 4, backgroundColor: '#fff', marginTop: 4 },
    metricRow: { alignItems: 'center' }
});
