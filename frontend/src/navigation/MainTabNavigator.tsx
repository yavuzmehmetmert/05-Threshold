import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { LayoutDashboard, User, Calendar as CalendarIcon } from 'lucide-react-native';
import DailyCockpitScreen from '../screens/DailyCockpitScreen';
import ProfileScreen from '../screens/ProfileScreen';
import CalendarScreen from '../screens/CalendarScreen';

const Tab = createBottomTabNavigator();

const MainTabNavigator = () => {
    return (
        <Tab.Navigator
            screenOptions={{
                headerShown: false,
                tabBarStyle: {
                    backgroundColor: '#050505',
                    borderTopColor: '#222',
                    height: 80,
                    paddingTop: 10,
                },
                tabBarActiveTintColor: '#CCFF00',
                tabBarInactiveTintColor: '#666',
                tabBarLabelStyle: {
                    fontSize: 12,
                    marginBottom: 10,
                },
            }}
        >
            <Tab.Screen
                name="Dashboard"
                component={DailyCockpitScreen}
                options={{
                    tabBarIcon: ({ color }) => <LayoutDashboard color={color} size={24} />,
                }}
            />
            <Tab.Screen
                name="Calendar"
                component={CalendarScreen}
                options={{
                    tabBarIcon: ({ color }) => <CalendarIcon color={color} size={24} />
                }}
            />
            <Tab.Screen
                name="Profile"
                component={ProfileScreen}
                options={{
                    tabBarIcon: ({ color }) => <User color={color} size={24} />,
                }}
            />
        </Tab.Navigator>
    );
};

export default MainTabNavigator;
