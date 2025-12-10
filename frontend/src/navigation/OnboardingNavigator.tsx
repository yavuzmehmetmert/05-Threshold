import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import WelcomeScreen from '../screens/onboarding/WelcomeScreen';
import LoginScreen from '../screens/onboarding/LoginScreen';
import SyncScreen from '../screens/onboarding/SyncScreen';
import ProfileSetupScreen from '../screens/onboarding/ProfileSetupScreen';
import GoalsScreen from '../screens/onboarding/GoalsScreen';
import GearScreen from '../screens/onboarding/GearScreen';
import DevicesScreen from '../screens/onboarding/DevicesScreen';
import ContextScreen from '../screens/onboarding/ContextScreen';

const Stack = createNativeStackNavigator();

const OnboardingNavigator = () => {
    return (
        <Stack.Navigator screenOptions={{ headerShown: false }}>
            <Stack.Screen name="Welcome" component={WelcomeScreen} />
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Sync" component={SyncScreen} />
            <Stack.Screen name="ProfileSetup" component={ProfileSetupScreen} />
            <Stack.Screen name="Devices" component={DevicesScreen} />
            <Stack.Screen name="Gear" component={GearScreen} />
            <Stack.Screen name="Context" component={ContextScreen} />
            <Stack.Screen name="Goals" component={GoalsScreen} />
        </Stack.Navigator>
    );
};

export default OnboardingNavigator;
