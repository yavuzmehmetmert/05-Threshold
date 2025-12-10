import React from 'react';
import { ScrollView, Platform } from 'react-native';
import { YStack, XStack, Text, Input, Label, Switch, Button, H2, Separator, Select, Adapt, Sheet } from 'tamagui';
import { Check, ChevronDown, ChevronUp } from '@tamagui/lucide-icons';
import { useOnboardingStore } from '../store/useOnboardingStore';

const SelectItem = ({ value, label, index }: { value: string; label: string; index: number }) => (
    <Select.Item index={index} key={value} value={value}>
        <Select.ItemText>{label}</Select.ItemText>
        <Select.ItemIndicator marginLeft="auto">
            <Check size={16} />
        </Select.ItemIndicator>
    </Select.Item>
);

const CustomSelect = ({
    value,
    onValueChange,
    items,
    placeholder
}: {
    value: string;
    onValueChange: (val: string) => void;
    items: { value: string; label: string }[];
    placeholder: string;
}) => {
    return (
        <Select value={value} onValueChange={onValueChange} disablePreventBodyScroll>
            <Select.Trigger width="100%" iconAfter={ChevronDown}>
                <Select.Value placeholder={placeholder} />
            </Select.Trigger>

            <Adapt when={"sm" as any} platform="touch">
                <Sheet modal dismissOnSnapToBottom>
                    <Sheet.Frame>
                        <Sheet.ScrollView>
                            <Adapt.Contents />
                        </Sheet.ScrollView>
                    </Sheet.Frame>
                    <Sheet.Overlay />
                </Sheet>
            </Adapt>

            <Select.Content zIndex={200000}>
                <Select.ScrollUpButton alignItems="center" justifyContent="center" position="relative" width="100%" height="$3">
                    <ChevronUp size={20} />
                </Select.ScrollUpButton>

                <Select.Viewport minWidth={200}>
                    <Select.Group>
                        <Select.Label>{placeholder}</Select.Label>
                        {items.map((item, i) => (
                            <SelectItem key={item.value} index={i} value={item.value} label={item.label} />
                        ))}
                    </Select.Group>
                </Select.Viewport>

                <Select.ScrollDownButton alignItems="center" justifyContent="center" position="relative" width="100%" height="$3">
                    <ChevronDown size={20} />
                </Select.ScrollDownButton>
            </Select.Content>
        </Select>
    );
};

const OnboardingScreen = () => {
    const store = useOnboardingStore();

    return (
        <ScrollView contentContainerStyle={{ flexGrow: 1, backgroundColor: '#050505', padding: 20 }}>
            <YStack space="$4" maxWidth={600} alignSelf="center" width="100%">
                <H2 color="#CCFF00" marginBottom="$2">Physiological Profile</H2>
                <Text color="$gray10" marginBottom="$4">
                    Calibrate the algorithm with your Genesis Vectors.
                </Text>

                {/* Race Date */}
                <YStack space="$2">
                    <Label color="white">Target Race Date (YYYY-MM-DD)</Label>
                    <Input
                        value={store.raceDate}
                        onChangeText={store.setRaceDate}
                        placeholder="2024-12-31"
                        backgroundColor="$background"
                        borderColor="$borderColor"
                        color="white"
                    />
                </YStack>

                {/* Race Type */}
                <YStack space="$2">
                    <Label color="white">Race Type</Label>
                    <CustomSelect
                        value={store.raceType}
                        onValueChange={(val) => store.setRaceType(val as any)}
                        items={[
                            { value: 'Marathon', label: 'Marathon' },
                            { value: 'Half Marathon', label: 'Half Marathon' },
                            { value: '5K', label: '5K' },
                        ]}
                        placeholder="Select Race Type"
                    />
                </YStack>

                <Separator borderColor="$gray5" />

                {/* Capacity Baseline */}
                <YStack space="$2">
                    <Label color="white">Avg Weekly Volume (last 6 months) [km]</Label>
                    <Input
                        value={store.weeklyVolume}
                        onChangeText={store.setWeeklyVolume}
                        keyboardType="numeric"
                        placeholder="e.g. 50"
                        backgroundColor="$background"
                        borderColor="$borderColor"
                        color="white"
                    />
                </YStack>

                {/* Current Level */}
                <YStack space="$2">
                    <Label color="white">Recent Race Time (5K/10K) [MM:SS]</Label>
                    <Input
                        value={store.recentRaceTime}
                        onChangeText={store.setRecentRaceTime}
                        placeholder="e.g. 25:00"
                        backgroundColor="$background"
                        borderColor="$borderColor"
                        color="white"
                    />
                </YStack>

                {/* Logistic Constraint */}
                <YStack space="$2">
                    <Label color="white">Daily Training Limit [min]</Label>
                    <Input
                        value={store.dailyTrainingLimit}
                        onChangeText={store.setDailyTrainingLimit}
                        keyboardType="numeric"
                        placeholder="e.g. 60"
                        backgroundColor="$background"
                        borderColor="$borderColor"
                        color="white"
                    />
                </YStack>

                <Separator borderColor="$gray5" />

                {/* Injury History */}
                <XStack alignItems="center" justifyContent="space-between">
                    <Label color="white">Bone Stress Injury History?</Label>
                    <Switch
                        checked={store.injuryHistory}
                        onCheckedChange={store.setInjuryHistory}
                        size="$4"
                    >
                        <Switch.Thumb animation={"quicker" as any} />
                    </Switch>
                </XStack>

                {/* Surface Type */}
                <YStack space="$2">
                    <Label color="white">Dominant Surface</Label>
                    <CustomSelect
                        value={store.surfaceType}
                        onValueChange={(val) => store.setSurfaceType(val as any)}
                        items={[
                            { value: 'Road', label: 'Road' },
                            { value: 'Trail', label: 'Trail' },
                            { value: 'Mixed', label: 'Mixed' },
                        ]}
                        placeholder="Select Surface"
                    />
                </YStack>

                {/* Risk Appetite */}
                <YStack space="$2">
                    <Label color="white">Risk Tolerance</Label>
                    <CustomSelect
                        value={store.riskTolerance}
                        onValueChange={(val) => store.setRiskTolerance(val as any)}
                        items={[
                            { value: 'Low', label: 'Low (Conservative)' },
                            { value: 'Medium', label: 'Medium (Balanced)' },
                            { value: 'High', label: 'High (Aggressive)' },
                        ]}
                        placeholder="Select Risk Level"
                    />
                </YStack>

                <Button
                    backgroundColor="#CCFF00"
                    color="#050505"
                    marginTop="$4"
                    pressStyle={{ opacity: 0.8 }}
                    onPress={() => alert('Profile Saved!')}
                >
                    Save Profile
                </Button>
            </YStack>
        </ScrollView>
    );
};

export default OnboardingScreen;
