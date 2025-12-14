import React from 'react';
import { useFonts } from 'expo-font';
// import '@tamagui/core/reset.css';
// import './tamagui-web.css';
import { TamaguiProvider, Theme } from 'tamagui';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View, Platform, Text } from 'react-native';
import OnboardingNavigator from './src/navigation/OnboardingNavigator';
import { useDashboardStore } from './src/store/useDashboardStore';
import MainTabNavigator from './src/navigation/MainTabNavigator';
import ActivityDetailScreen from './src/screens/ActivityDetailScreen';
import LiveActivityScreen from './src/screens/LiveActivityScreen';
import WeekDetailScreen from './src/screens/WeekDetailScreen';
import config from './tamagui.config';

const Stack = createNativeStackNavigator<RootStackParamList>();

// Navigation Types
export type RootStackParamList = {
    Onboarding: undefined;
    MainTab: undefined;
    ActivityDetail: { activity: any };
    LiveActivity: undefined;
    WeekDetail: { startDate: string; endDate: string; weekLabel: string };
};

const NavTheme = {
    ...DarkTheme,
    colors: {
        ...DarkTheme.colors,
        background: '#050505',
        card: '#050505',
        border: '#121212',
    },
};

export default function App() {
    const [fontsLoaded] = useFonts({
        Inter: require('@tamagui/font-inter/otf/Inter-Medium.otf'),
        InterBold: require('@tamagui/font-inter/otf/Inter-Bold.otf'),
    });

    const isOnboarded = useDashboardStore(state => state.isOnboarded);

    React.useEffect(() => {
        if (Platform.OS === 'web') {
            document.body.style.backgroundColor = '#050505';
        }
    }, []);

    if (!fontsLoaded) {
        return (
            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#050505' }}>
                <ActivityIndicator size="large" color="#CCFF00" />
            </View>
        );
    }

    return (
        <TamaguiProvider config={config} defaultTheme="dark">
            <Theme name="dark">
                <NavigationContainer theme={NavTheme}>
                    <StatusBar style="light" />
                    <Stack.Navigator screenOptions={{ headerShown: false }}>
                        {isOnboarded ? (
                            <>
                                <Stack.Screen name="MainTab" component={MainTabNavigator} />
                                <Stack.Screen name="ActivityDetail" component={ActivityDetailScreen} />
                                <Stack.Screen name="LiveActivity" component={LiveActivityScreen} />
                                <Stack.Screen name="WeekDetail" component={WeekDetailScreen} />
                            </>
                        ) : (
                            <Stack.Screen name="Onboarding" component={OnboardingNavigator} />
                        )}
                    </Stack.Navigator>
                </NavigationContainer>
            </Theme>
        </TamaguiProvider >
    );
}
