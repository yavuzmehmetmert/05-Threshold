import React from 'react';
import { ScrollView } from 'react-native';
import { YStack, Text, H2, Slider, Label, Separator, Button, XStack } from 'tamagui';
import { useCheckInStore } from '../store/useCheckInStore';

const MorningCheckInScreen = () => {
    const store = useCheckInStore();

    return (
        <ScrollView contentContainerStyle={{ flexGrow: 1, backgroundColor: '#050505', padding: 20 }}>
            <YStack space="$5" maxWidth={600} alignSelf="center" width="100%">
                <H2 color="#CCFF00">Morning Check-In</H2>
                <Text color="$gray10">
                    Daily calibration for your Readiness Score.
                </Text>

                <Separator borderColor="$gray5" />

                {/* Freshness Override */}
                <YStack space="$4">
                    <XStack justifyContent="space-between">
                        <Label color="white">Freshness Override</Label>
                        <Text color="$yellow10" fontWeight="bold">{store.freshnessOverride}</Text>
                    </XStack>
                    <Text color="$gray11" fontSize="$2">
                        -60 (Exhausted) to +60 (Super Fresh)
                    </Text>
                    <Slider
                        value={[store.freshnessOverride]}
                        onValueChange={(val) => store.setFreshnessOverride(val[0])}
                        min={-60}
                        max={60}
                        step={1}
                    >
                        <Slider.Track backgroundColor="$gray5">
                            <Slider.TrackActive backgroundColor="#CCFF00" />
                        </Slider.Track>
                        <Slider.Thumb index={0} circular size="$1" backgroundColor="white" />
                    </Slider>
                </YStack>

                <Separator borderColor="$gray5" />

                {/* Soreness Score */}
                <YStack space="$4">
                    <XStack justifyContent="space-between">
                        <Label color="white">Soreness Score (1-10)</Label>
                        <Text color="$red10" fontWeight="bold">{store.sorenessScore}</Text>
                    </XStack>
                    <Text color="$gray11" fontSize="$2">
                        1 (No Pain) - 10 (Severe Pain)
                    </Text>
                    <Slider
                        value={[store.sorenessScore]}
                        onValueChange={(val) => store.setSorenessScore(val[0])}
                        min={1}
                        max={10}
                        step={1}
                    >
                        <Slider.Track backgroundColor="$gray5">
                            <Slider.TrackActive backgroundColor="#FF3333" />
                        </Slider.Track>
                        <Slider.Thumb index={0} circular size="$1" backgroundColor="white" />
                    </Slider>
                </YStack>

                <Separator borderColor="$gray5" />

                {/* Mental Stress */}
                <YStack space="$4">
                    <XStack justifyContent="space-between">
                        <Label color="white">Mental / Work Stress (1-5)</Label>
                        <Text color="$blue10" fontWeight="bold">{store.mentalStress}</Text>
                    </XStack>
                    <Text color="$gray11" fontSize="$2">
                        1 (Low) - 5 (High)
                    </Text>
                    <Slider
                        value={[store.mentalStress]}
                        onValueChange={(val) => store.setMentalStress(val[0])}
                        min={1}
                        max={5}
                        step={1}
                    >
                        <Slider.Track backgroundColor="$gray5">
                            <Slider.TrackActive backgroundColor="$blue10" />
                        </Slider.Track>
                        <Slider.Thumb index={0} circular size="$1" backgroundColor="white" />
                    </Slider>
                </YStack>

                <Button
                    backgroundColor="#CCFF00"
                    color="#050505"
                    marginTop="$4"
                    pressStyle={{ opacity: 0.8 }}
                    onPress={() => alert('Check-In Submitted!')}
                >
                    Submit Readiness
                </Button>
            </YStack>
        </ScrollView>
    );
};

export default MorningCheckInScreen;
