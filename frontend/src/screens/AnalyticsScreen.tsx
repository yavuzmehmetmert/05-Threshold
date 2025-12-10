import React from 'react';
import { ScrollView, Dimensions } from 'react-native';
import { YStack, XStack, Text, H2, H4, Card, Separator } from 'tamagui';
import { VictoryChart, VictoryLine, VictoryArea, VictoryAxis, VictoryTheme, VictoryBar, VictoryLabel } from 'victory-native';
import { useAnalyticsStore } from '../store/useAnalyticsStore';

const AnalyticsScreen = () => {
    const store = useAnalyticsStore();
    const screenWidth = Dimensions.get('window').width;

    return (
        <ScrollView contentContainerStyle={{ flexGrow: 1, backgroundColor: '#050505', padding: 20 }}>
            <YStack space="$5" maxWidth={600} alignSelf="center" width="100%">
                <H2 color="#CCFF00">Performance Analytics</H2>
                <Text color="$gray10">Longitudinal Analysis (PMC)</Text>

                {/* PMC Chart */}
                <Card bordered padding="$2" backgroundColor="$background" borderColor="$borderColor">
                    <YStack>
                        <H4 color="white" paddingLeft="$2" paddingTop="$2">Fitness (CTL) vs Fatigue (ATL)</H4>
                        <VictoryChart
                            width={screenWidth - 60}
                            height={250}
                            theme={VictoryTheme.material}
                            padding={{ top: 20, bottom: 40, left: 40, right: 20 }}
                        >
                            <VictoryAxis
                                tickFormat={(t) => t.slice(5)}
                                style={{
                                    axis: { stroke: "#888" },
                                    tickLabels: { fill: "#888", fontSize: 10 }
                                }}
                            />
                            <VictoryAxis
                                dependentAxis
                                style={{
                                    axis: { stroke: "#888" },
                                    tickLabels: { fill: "#888", fontSize: 10 }
                                }}
                            />

                            {/* ATL Area */}
                            <VictoryArea
                                data={store.pmcData}
                                x="date"
                                y="atl"
                                style={{ data: { fill: "rgba(255, 51, 51, 0.3)", stroke: "#FF3333", strokeWidth: 2 } }}
                            />

                            {/* CTL Line */}
                            <VictoryLine
                                data={store.pmcData}
                                x="date"
                                y="ctl"
                                style={{ data: { stroke: "#00CCFF", strokeWidth: 3 } }}
                            />
                        </VictoryChart>
                    </YStack>
                </Card>

                {/* TSB Chart */}
                <Card bordered padding="$2" backgroundColor="$background" borderColor="$borderColor">
                    <YStack>
                        <H4 color="white" paddingLeft="$2" paddingTop="$2">Form (TSB)</H4>
                        <VictoryChart
                            width={screenWidth - 60}
                            height={150}
                            theme={VictoryTheme.material}
                            padding={{ top: 20, bottom: 40, left: 40, right: 20 }}
                        >
                            <VictoryAxis
                                tickFormat={(t) => t.slice(5)}
                                style={{
                                    axis: { stroke: "#888" },
                                    tickLabels: { fill: "#888", fontSize: 10 }
                                }}
                            />
                            <VictoryAxis
                                dependentAxis
                                style={{
                                    axis: { stroke: "#888" },
                                    tickLabels: { fill: "#888", fontSize: 10 }
                                }}
                            />
                            <VictoryBar
                                data={store.pmcData}
                                x="date"
                                y="tsb"
                                style={{
                                    data: {
                                        fill: ({ datum }) => datum.tsb >= 0 ? "#CCFF00" : "#FF3333"
                                    }
                                }}
                            />
                        </VictoryChart>
                    </YStack>
                </Card>

                <Separator borderColor="$gray5" />

                {/* Risk Metrics */}
                <XStack space="$3">
                    <Card bordered padding="$4" flex={1} backgroundColor="$background" borderColor="$borderColor">
                        <YStack space="$2">
                            <Text color="$gray11" fontSize="$2">Injury Risk (ACWR)</Text>
                            <H2 color={store.acwr >= 1.5 ? "#FF3333" : "#CCFF00"}>{store.acwr}</H2>
                            <Text color="$gray10" fontSize="$2">Target: &lt; 1.5</Text>
                        </YStack>
                    </Card>
                    <Card bordered padding="$4" flex={1} backgroundColor="$background" borderColor="$borderColor">
                        <YStack space="$2">
                            <Text color="$gray11" fontSize="$2">Ramp Rate</Text>
                            <H2 color={store.rampRate > 20 ? "#FF3333" : "#CCFF00"}>{store.rampRate}%</H2>
                            <Text color="$gray10" fontSize="$2">Target: &lt; 20%</Text>
                        </YStack>
                    </Card>
                </XStack>

            </YStack>
        </ScrollView>
    );
};

export default AnalyticsScreen;
