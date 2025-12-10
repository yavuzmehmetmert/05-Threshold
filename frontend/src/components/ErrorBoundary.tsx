import React, { Component, ErrorInfo, ReactNode } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("ErrorBoundary caught an error", error, errorInfo);
        this.setState({ errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <View style={styles.container}>
                    <ScrollView contentContainerStyle={styles.scroll}>
                        <Text style={styles.title}>Something went wrong.</Text>
                        <Text style={styles.errorType}>{this.state.error?.toString()}</Text>
                        <View style={styles.box}>
                            <Text style={styles.stackTrace}>
                                {this.state.errorInfo?.componentStack}
                            </Text>
                        </View>
                        <TouchableOpacity
                            style={styles.button}
                            onPress={() => this.setState({ hasError: false })}
                        >
                            <Text style={styles.buttonText}>Try Again</Text>
                        </TouchableOpacity>
                    </ScrollView>
                </View>
            );
        }

        return this.props.children;
    }
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#1A0000', // Dark Red background for error
        padding: 20,
        justifyContent: 'center',
    },
    scroll: {
        flexGrow: 1,
        justifyContent: 'center',
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#FF3333',
        marginBottom: 10,
        textAlign: 'center',
    },
    errorType: {
        fontSize: 16,
        color: 'white',
        marginBottom: 20,
        textAlign: 'center',
    },
    box: {
        backgroundColor: '#000',
        padding: 10,
        borderRadius: 8,
        marginBottom: 20,
    },
    stackTrace: {
        color: '#FFCC00',
        fontFamily: 'monospace',
        fontSize: 12,
    },
    button: {
        backgroundColor: '#FF3333',
        padding: 15,
        borderRadius: 8,
        alignItems: 'center',
    },
    buttonText: {
        color: 'white',
        fontWeight: 'bold',
    }
});
