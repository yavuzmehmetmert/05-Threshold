import React from 'react';
import { ScrollView } from 'react-native';
import { YStack, XStack, Text, Card, Button, Progress, Circle, Theme } from 'tamagui';
import { Battery, Activity, Zap, ArrowRight } from 'lucide-react-native';
import { VictoryPie, VictoryLabel } from 'victory-native';

// Mock Data (Backend entegrasyonu sonra yapılacak)
const readinessScore = 85;
const bodyBattery = 72;
const todaysMission = {
    type: "Interval Run",
    duration: "45 min",
    description: "5x4 min Threshold @ 170-175 bpm",
    rpe: 8
};

const ReadinessGauge = ({ score }: { score: number }) => {
    const getColor = (s: number) => {
        if (s >= 80) return "#CCFF00"; // Green
        if (s >= 50) return "#FFCC00"; // Yellow
        return "#FF3333"; // Red
    };

    return (
        <YStack alignItems="center" justifyContent="center" height={250}>
            <VictoryPie
                standalone={true}
                width={250}
                height={250}
                data={[
                    { x: 1, y: score },
                    { x: 2, y: 100 - score }
                ]}
                innerRadius={90}
                cornerRadius={25}
                labels={() => null}
                style={{
                    data: {
                        fill: ({ datum }) => datum.x === 1 ? getColor(score) : "#1a1a1a"
                    }
                }}
            />
            <YStack position="absolute" alignItems="center">
                <Text fontSize={48} fontWeight="bold" color={getColor(score)}>{score}</Text>
                <Text fontSize={14} color="$textMuted">READINESS</Text>
            </YStack>
        </YStack>
    );
};

const MetricCard = ({ title, value, icon: Icon, color }: any) => (
    <Card flex={1} backgroundColor="$surface" padding="$3" borderRadius="$4" bordered>
        <YStack space="$2">
            <XStack justifyContent="space-between" alignItems="center">
                <Icon size={20} color={color} />
                <Text fontSize={12} color="$textMuted">{title}</Text>
            </XStack>
            <Text fontSize={24} fontWeight="bold" color="$text">{value}</Text>
        </YStack>
    </Card>
);

export default function DashboardScreen() {
    return (
        <Theme name="dark">
            <ScrollView style={{ flex: 1, backgroundColor: '#050505' }} contentContainerStyle={{ padding: 20, paddingBottom: 100 }}>
                <YStack space="$5" marginTop="$8">

                    {/* Header */}
                    <XStack justifyContent="space-between" alignItems="center">
                        <YStack>
                            <Text fontSize={28} fontWeight="bold" color="$text">Good Morning,</Text>
                            <Text fontSize={28} fontWeight="bold" color="$primary">Athlete</Text>
                        </YStack>
                        <Circle size={40} backgroundColor="$surface">
                            <UserIcon />
                        </Circle>
                    </XStack>

                    {/* Readiness Gauge */}
                    <ReadinessGauge score={readinessScore} />

                    {/* Key Metrics */}
                    <XStack space="$3">
                        <MetricCard
                            title="BODY BATTERY"
                            value={`${bodyBattery}%`}
                            icon={Battery}
                            color="#00CCFF"
                        />
                        <MetricCard
                            title="HRV STATUS"
                            value="Balanced"
                            icon={Activity}
                            color="#CCFF00"
                        />
                    </XStack>

                    {/* Today's Mission */}
                    <YStack space="$2">
                        <Text fontSize={16} fontWeight="bold" color="$textMuted" marginLeft="$1">TODAY'S MISSION</Text>
                        <Card backgroundColor="$surface" padding="$4" borderRadius="$4" bordered>
                            <YStack space="$3">
                                <XStack justifyContent="space-between" alignItems="center">
                                    <XStack space="$2" alignItems="center">
                                        <Zap size={20} color="#CCFF00" />
                                        <Text fontSize={18} fontWeight="bold" color="$text">{todaysMission.type}</Text>
                                    </XStack>
                                    <Text fontSize={14} color="$textMuted">{todaysMission.duration}</Text>
                                </XStack>

                                <Text fontSize={14} color="$textMuted">{todaysMission.description}</Text>

                                <XStack space="$2" marginTop="$2">
                                    <Text fontSize={12} color="$textMuted" backgroundColor="#1a1a1a" paddingHorizontal="$2" paddingVertical="$1" borderRadius="$2">
                                        Target RPE: {todaysMission.rpe}
                                    </Text>
                                </XStack>

                                <Button backgroundColor="$primary" color="black" iconAfter={ArrowRight} marginTop="$2">
                                    Start Activity
                                </Button>
                            </YStack>
                        </Card>
                    </YStack>

                </YStack>
            </ScrollView>
        </Theme>
    );
}

const UserIcon = () => (
    <Text fontSize={18}>👤</Text>
);
