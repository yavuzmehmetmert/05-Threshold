import { useNavigation } from '@react-navigation/native';
import React, { useEffect } from 'react';
import { Dimensions, ScrollView, TouchableOpacity } from 'react-native';
import { YStack, XStack, Text, Card, Button, Circle, Theme, View } from 'tamagui';
import { Battery, Activity, Zap, ArrowRight, User, Calendar, Clock, MapPin, RefreshCw } from 'lucide-react-native';
import { VictoryPie } from 'victory-native';
import Animated, {
    useSharedValue,
    useAnimatedStyle,
    withRepeat,
    withTiming,
    withSequence,
    withSpring,
    withDelay,
    FadeInDown,
} from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { useDashboardStore } from '../store/useDashboardStore';

// --- COMPONENTS ---

const AnimatedCard = Animated.createAnimatedComponent(Card);

const GlassCard = ({ children, delay = 0, style, ...props }: any) => {
    return (
        <Animated.View
            entering={FadeInDown.delay(delay).springify()}
            style={[{ borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' }, style]}
        >
            <BlurView intensity={20} tint="dark" style={{ padding: 16, backgroundColor: 'rgba(0,0,0,0.5)' }}>
                {children}
            </BlurView>
        </Animated.View>
    );
};

const ReadinessGauge = ({ score }: { score: number }) => {
    const pulse = useSharedValue(1);
    const progress = useSharedValue(0);

    useEffect(() => {
        pulse.value = withRepeat(
            withSequence(
                withTiming(1.05, { duration: 1500 }),
                withTiming(1, { duration: 1500 })
            ),
            -1,
            true
        );
        progress.value = withDelay(500, withSpring(score, { damping: 20 }));
    }, []);

    const animatedStyle = useAnimatedStyle(() => ({
        transform: [{ scale: pulse.value }]
    }));

    const getColor = (s: number) => {
        if (s >= 80) return "#CCFF00"; // Neon Green
        if (s >= 50) return "#FFCC00"; // Neon Yellow
        return "#FF3333"; // Neon Red
    };

    const color = getColor(score);

    return (
        <YStack alignItems="center" justifyContent="center" height={280} position="relative">
            {/* Background Glow */}
            <Animated.View style={[{ position: 'absolute', width: 200, height: 200, borderRadius: 100, backgroundColor: color, opacity: 0.15 }, animatedStyle]} />

            <VictoryPie
                standalone={true}
                width={260}
                height={260}
                data={[
                    { x: 1, y: score },
                    { x: 2, y: 100 - score }
                ]}
                innerRadius={95}
                cornerRadius={12}
                labels={() => null}
                style={{
                    data: {
                        fill: ({ datum }) => datum.x === 1 ? color : "rgba(255,255,255,0.05)"
                    }
                }}
            />
            <YStack position="absolute" alignItems="center">
                <Animated.View style={animatedStyle}>
                    <Text fontSize={64} fontWeight="900" color={color} textShadowColor={color} textShadowRadius={10}>{score}</Text>
                </Animated.View>
                <Text fontSize={12} color="$color.gray10" letterSpacing={2} fontWeight="600">READINESS</Text>
            </YStack>
        </YStack>
    );
};

const MetricCard = ({ title, value, icon: Icon, color, delay }: any) => (
    <Animated.View style={{ flex: 1 }} entering={FadeInDown.delay(delay).springify()}>
        <View
            borderRadius={16}
            borderWidth={1}
            borderColor="rgba(255,255,255,0.08)"
            backgroundColor="rgba(20,20,20,0.6)"
            padding="$3"
        >
            <YStack space="$2">
                <XStack justifyContent="space-between" alignItems="center">
                    <Icon size={18} color={color} />
                    <Text fontSize={11} color="$color.gray9" letterSpacing={1} fontWeight="600">{title}</Text>
                </XStack>
                <Text fontSize={28} fontWeight="bold" color="$color.gray12">{value}</Text>
            </YStack>
        </View>
    </Animated.View>
);

const ActivityItem = ({ activity, index, onPress }: any) => {
    return (
        <Animated.View entering={FadeInDown.delay(800 + (index * 100)).springify()}>
            <TouchableOpacity onPress={onPress}>
                <View
                    borderRadius={12}
                    backgroundColor="rgba(255,255,255,0.03)"
                    borderWidth={1}
                    borderColor="rgba(255,255,255,0.05)"
                    padding="$3"
                    marginBottom="$3"
                    pressStyle={{ backgroundColor: "rgba(255,255,255,0.08)" }}
                >
                    <XStack justifyContent="space-between" alignItems="center">
                        <XStack space="$3" alignItems="center">
                            <View backgroundColor="rgba(204, 255, 0, 0.1)" padding="$2" borderRadius="$3">
                                <Activity size={20} color="#CCFF00" />
                            </View>
                            <YStack>
                                <Text fontSize={16} fontWeight="bold" color="$color.gray12">{activity.activityName}</Text>
                                <XStack space="$2" marginTop={2}>
                                    <Calendar size={12} color="#888" />
                                    <Text fontSize={12} color="$color.gray10">{new Date(activity.startTimeLocal).toLocaleDateString()}</Text>
                                </XStack>
                            </YStack>
                        </XStack>
                        <YStack alignItems="flex-end">
                            <Text fontSize={16} fontWeight="bold" color="$color.neonGreen">{(activity.distance / 1000).toFixed(2)} km</Text>
                            <Text fontSize={12} color="$color.gray10">
                                {Math.floor(activity.duration / 60)}h {Math.floor(activity.duration % 60)}m
                            </Text>
                        </YStack>
                    </XStack>
                </View>
            </TouchableOpacity>
        </Animated.View>
    );
};

export default function DashboardScreen() {
    const navigation = useNavigation<any>();
    const { readinessScore, activities, setActivities } = useDashboardStore();
    const [refreshing, setRefreshing] = React.useState(false);
    const [syncing, setSyncing] = React.useState(false);

    // Sync animation
    const syncRotation = useSharedValue(0);

    const syncAnimatedStyle = useAnimatedStyle(() => ({
        transform: [{ rotate: `${syncRotation.value}deg` }]
    }));

    React.useEffect(() => {
        if (syncing) {
            syncRotation.value = withRepeat(
                withTiming(360, { duration: 1000 }),
                -1,
                false
            );
        } else {
            syncRotation.value = 0;
        }
    }, [syncing]);

    const handleSync = async () => {
        if (syncing) return;
        setSyncing(true);
        try {
            const response = await fetch('http://localhost:8000/ingestion/sync/incremental', {
                method: 'POST'
            });
            const result = await response.json();
            console.log('Sync result:', result);

            // Refresh all dashboard data
            await Promise.all([
                fetchActivities(),
                fetchPmc(),
                fetchWeekly()
            ]);
        } catch (error) {
            console.error('Sync failed:', error);
        } finally {
            setSyncing(false);
        }
    };

    // PMC State
    const [pmc, setPmc] = React.useState<{
        ctl: number;
        atl: number;
        tsb: number;
        form_status: string;
        form_emoji: string;
        weekly_tss: number;
        is_overreaching: boolean;
    } | null>(null);

    // Weekly breakdown state
    const [weeklyData, setWeeklyData] = React.useState<{
        current_week: { start: string; tss: number; days_completed: number; projected_tss: number };
        weekly_history: Array<{ week_start: string; week_number: number; tss: number }>;
        avg_weekly_tss: number;
        trend: string;
        trend_emoji: string;
    } | null>(null);

    useEffect(() => {
        fetchActivities();
        fetchPmc();
        fetchWeekly();
    }, []);

    const fetchPmc = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/training-load');
            const data = await response.json();
            setPmc(data);
        } catch (error) {
            console.error('Failed to fetch PMC:', error);
        }
    };

    const fetchWeekly = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/training-load/weekly');
            const data = await response.json();
            setWeeklyData(data);
        } catch (error) {
            console.error('Failed to fetch weekly data:', error);
        }
    };

    const fetchActivities = async () => {
        try {
            setRefreshing(true);
            const response = await fetch('http://localhost:8000/ingestion/activities?limit=10');
            const data = await response.json();
            if (Array.isArray(data)) {
                setActivities(data);
            }
        } catch (error) {
            console.error('Failed to fetch activities:', error);
        } finally {
            setRefreshing(false);
        }
    };

    // Assuming bodyBattery and todayWorkout are still available from the store or other means if needed
    // For this change, they are removed from the direct destructuring as per instruction.
    const { bodyBattery, todayWorkout } = useDashboardStore(); // Re-add if they are used later and not meant to be removed

    return (
        <Theme name="dark">
            <LinearGradient
                colors={['#000000', '#0a0a0a', '#111111']}
                style={{ flex: 1 }}
            >
                <ScrollView
                    style={{ flex: 1 }}
                    contentContainerStyle={{ padding: 20, paddingBottom: 120, paddingTop: 60 }}
                    showsVerticalScrollIndicator={false}
                >
                    <YStack space="$6">

                        {/* Header */}
                        <Animated.View entering={FadeInDown.duration(800)}>
                            <XStack justifyContent="space-between" alignItems="center">
                                <YStack>
                                    <Text fontSize={16} color="$color.gray10" fontFamily="$body">Welcome back,</Text>
                                    <Text fontSize={32} fontWeight="900" color="$color.gray12" letterSpacing={-0.5} textTransform="uppercase">
                                        Agent <Text color="$color.neonGreen">007</Text>
                                    </Text>
                                </YStack>
                                <XStack space="$3" alignItems="center">
                                    <TouchableOpacity onPress={handleSync} disabled={syncing}>
                                        <Circle size={48} backgroundColor={syncing ? "rgba(204,255,0,0.15)" : "rgba(255,255,255,0.05)"} borderWidth={1} borderColor={syncing ? "rgba(204,255,0,0.3)" : "rgba(255,255,255,0.1)"}>
                                            <Animated.View style={syncAnimatedStyle}>
                                                <RefreshCw size={22} color={syncing ? "#CCFF00" : "#fff"} />
                                            </Animated.View>
                                        </Circle>
                                    </TouchableOpacity>
                                    <Circle size={48} backgroundColor="rgba(255,255,255,0.05)" borderWidth={1} borderColor="rgba(255,255,255,0.1)">
                                        <User size={24} color="#fff" />
                                    </Circle>
                                </XStack>
                            </XStack>
                        </Animated.View>

                        {/* Readiness Gauge */}
                        <ReadinessGauge score={readinessScore} />

                        {/* Key Metrics */}
                        <XStack space="$3">
                            <MetricCard
                                title="BODY BATTERY"
                                value={`${bodyBattery}%`}
                                icon={Battery}
                                color="#00CCFF"
                                delay={200}
                            />
                            <MetricCard
                                title="HRV STATUS"
                                value="Balanced"
                                icon={Activity}
                                color="#CCFF00"
                                delay={400}
                            />
                        </XStack>

                        {/* Training Load Card - Enhanced with Weekly Data */}
                        {pmc && (
                            <Animated.View entering={FadeInDown.delay(500).springify()}>
                                <View
                                    borderRadius={16}
                                    borderWidth={1}
                                    borderColor={pmc.is_overreaching ? "rgba(255,51,51,0.3)" : "rgba(255,255,255,0.08)"}
                                    backgroundColor={pmc.is_overreaching ? "rgba(255,51,51,0.1)" : "rgba(20,20,20,0.6)"}
                                    padding="$4"
                                >
                                    {/* Header with Form Status */}
                                    <XStack justifyContent="space-between" alignItems="center" marginBottom="$3">
                                        <XStack space="$2" alignItems="center">
                                            <Zap size={18} color="#FF9900" />
                                            <Text fontSize={12} color="$color.gray10" letterSpacing={1} fontWeight="bold">TRAINING LOAD</Text>
                                        </XStack>
                                        <XStack space="$2" alignItems="center">
                                            {weeklyData && (
                                                <Text fontSize={12} color="#888">{weeklyData.trend_emoji}</Text>
                                            )}
                                            <Text fontSize={16} color={pmc.tsb > 5 ? "#CCFF00" : pmc.tsb > -10 ? "#FFCC00" : "#FF3333"} fontWeight="bold">
                                                {pmc.form_emoji} {pmc.form_status}
                                            </Text>
                                        </XStack>
                                    </XStack>

                                    {/* CTL / ATL / TSB Row */}
                                    <XStack justifyContent="space-around" marginBottom="$3">
                                        <YStack alignItems="center">
                                            <Text fontSize={9} color="#888">FITNESS</Text>
                                            <Text fontSize={22} fontWeight="bold" color="#00CCFF">{pmc.ctl}</Text>
                                        </YStack>
                                        <YStack alignItems="center">
                                            <Text fontSize={9} color="#888">FATIGUE</Text>
                                            <Text fontSize={22} fontWeight="bold" color="#FF9900">{pmc.atl}</Text>
                                        </YStack>
                                        <YStack alignItems="center">
                                            <Text fontSize={9} color="#888">FORM</Text>
                                            <Text fontSize={22} fontWeight="bold" color={pmc.tsb > 5 ? "#CCFF00" : pmc.tsb > -10 ? "#FFCC00" : "#FF3333"}>
                                                {pmc.tsb > 0 ? '+' : ''}{pmc.tsb}
                                            </Text>
                                        </YStack>
                                    </XStack>

                                    <View height={1} backgroundColor="rgba(255,255,255,0.1)" marginBottom="$3" />

                                    {/* Current Week Progress */}
                                    {weeklyData && (
                                        <YStack marginBottom="$3">
                                            <XStack justifyContent="space-between" alignItems="center" marginBottom="$2">
                                                <Text fontSize={10} color="#888">THIS WEEK (Mon-Sun)</Text>
                                                <Text fontSize={11} color="#666">{weeklyData.current_week.days_completed}/7 days</Text>
                                            </XStack>
                                            <XStack justifyContent="space-between" alignItems="flex-end">
                                                <YStack>
                                                    <Text fontSize={28} fontWeight="bold" color="#CCFF00">{weeklyData.current_week.tss}</Text>
                                                    <Text fontSize={10} color="#666">TSS completed</Text>
                                                </YStack>
                                                <YStack alignItems="flex-end">
                                                    <Text fontSize={16} color="#888">{weeklyData.current_week.projected_tss}</Text>
                                                    <Text fontSize={10} color="#666">projected</Text>
                                                </YStack>
                                                <YStack alignItems="flex-end">
                                                    <Text fontSize={16} color="#666">{weeklyData.avg_weekly_tss}</Text>
                                                    <Text fontSize={10} color="#666">avg/week</Text>
                                                </YStack>
                                            </XStack>
                                        </YStack>
                                    )}

                                    {/* Weekly History Mini Chart (last 8 weeks) */}
                                    {weeklyData && weeklyData.weekly_history.length > 0 && (
                                        <YStack>
                                            <Text fontSize={10} color="#888" marginBottom="$2">WEEKLY HISTORY</Text>
                                            <XStack justifyContent="space-between" alignItems="flex-end" height={50}>
                                                {weeklyData.weekly_history.slice(-8).map((week, idx) => {
                                                    const maxTss = Math.max(...weeklyData.weekly_history.slice(-8).map(w => w.tss), 1);
                                                    const height = Math.max((week.tss / maxTss) * 45, 4);
                                                    const isRecent = idx >= 6;
                                                    return (
                                                        <YStack key={week.week_start} alignItems="center" flex={1} marginHorizontal={2}>
                                                            <View
                                                                backgroundColor={isRecent ? "#CCFF00" : "#444"}
                                                                width="80%"
                                                                height={height}
                                                                borderRadius={4}
                                                            />
                                                            <Text fontSize={8} color="#666" marginTop={4}>W{week.week_number}</Text>
                                                        </YStack>
                                                    );
                                                })}
                                            </XStack>
                                        </YStack>
                                    )}

                                    {pmc.is_overreaching && (
                                        <View backgroundColor="rgba(255,51,51,0.15)" padding="$2" borderRadius="$2" marginTop="$3">
                                            <Text fontSize={11} color="#FF3333" textAlign="center">⚠️ High fatigue detected. Consider recovery.</Text>
                                        </View>
                                    )}
                                </View>
                            </Animated.View>
                        )}

                        {/* Today's Mission */}
                        {todayWorkout && (
                            <YStack space="$3" marginTop="$2">
                                <Text fontSize={12} color="$color.gray10" letterSpacing={2} fontWeight="bold" marginLeft="$1">CURRENT OBJECTIVE</Text>

                                <GlassCard delay={600}>
                                    <YStack space="$4">
                                        <XStack justifyContent="space-between" alignItems="center">
                                            <XStack space="$3" alignItems="center">
                                                <View backgroundColor="rgba(204,255,0,0.1)" padding="$2" borderRadius="$3">
                                                    <Zap size={20} color="#CCFF00" />
                                                </View>
                                                <YStack>
                                                    <Text fontSize={18} fontWeight="bold" color="#fff">{todayWorkout.type}</Text>
                                                    <Text fontSize={12} color="$color.gray9">{todayWorkout.intensity}</Text>
                                                </YStack>
                                            </XStack>
                                            <Text fontSize={14} color="#CCFF00" fontWeight="bold">{todayWorkout.duration}</Text>
                                        </XStack>

                                        <View height={1} backgroundColor="rgba(255,255,255,0.1)" />

                                        <Text fontSize={15} color="$color.gray11" lineHeight={22}>{todayWorkout.description}</Text>

                                        <XStack gap="$2" flexWrap="wrap">
                                            <Text fontSize={11} color="$color.gray12" backgroundColor="rgba(255,255,255,0.05)" paddingHorizontal="$2" paddingVertical="$1" borderRadius="$2" overflow="hidden">
                                                Target RPE: 8
                                            </Text>
                                            <Text fontSize={11} color="$color.gray12" backgroundColor="rgba(255,255,255,0.05)" paddingHorizontal="$2" paddingVertical="$1" borderRadius="$2" overflow="hidden">
                                                Zone 4 Focus
                                            </Text>
                                        </XStack>

                                        <Button
                                            backgroundColor="#CCFF00"
                                            color="black"
                                            iconAfter={ArrowRight}
                                            fontWeight="bold"
                                            pressStyle={{ opacity: 0.8, scale: 0.98 }}
                                        >
                                            Engage Protocol
                                        </Button>
                                    </YStack>
                                </GlassCard>
                            </YStack>
                        )}

                        {/* Recent Activities */}
                        <YStack space="$3" marginTop="$2">
                            <XStack justifyContent="space-between" alignItems="center" marginBottom="$2">
                                <Text fontSize={12} color="$color.gray10" letterSpacing={2} fontWeight="bold" marginLeft="$1">RECENT OPERATIONS</Text>
                                <TouchableOpacity onPress={() => navigation.navigate('Activities')}>
                                    <Text fontSize={12} color="$color.neonGreen" fontWeight="bold">VIEW ALL</Text>
                                </TouchableOpacity>
                            </XStack>

                            {activities.slice(0, 3).map((activity, index) => (
                                <ActivityItem
                                    key={activity.activityId}
                                    activity={activity}
                                    index={index}
                                    onPress={() => navigation.navigate('ActivityDetail', { activityId: activity.activityId })}
                                />
                            ))}
                        </YStack>

                    </YStack>
                </ScrollView>
            </LinearGradient>
        </Theme>
    );
}
