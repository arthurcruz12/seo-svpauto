import React, { useEffect, useState } from 'react';
import { SafeAreaView, View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput } from 'react-native';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [insights, setInsights] = useState(null);
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const authHeaders = (withJson = false) => ({
    Authorization: `Bearer ${token}`,
    ...(withJson ? { 'Content-Type': 'application/json' } : {})
  });

  async function login() {
    setError('');
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Login failed');
      setToken(data.access_token);
    } catch (e) {
      setError(e.message);
    }
  }

  async function loadData() {
    if (!token) return;
    const dashboardResponse = await fetch(`${API_URL}/dashboard/1`, { headers: authHeaders() });
    if (!dashboardResponse.ok) throw new Error('Unable to load dashboard');
    const dashboardData = await dashboardResponse.json();
    setDashboard(dashboardData);

    const documentsResponse = await fetch(`${API_URL}/documents`, { headers: authHeaders() });
    const documentsData = await documentsResponse.json();
    setDocuments(documentsData);

    const insightsResponse = await fetch(`${API_URL}/companies/1/neuro-insights`, { headers: authHeaders() });
    const insightsData = await insightsResponse.json();
    setInsights(insightsData);
  }

  async function createDocument() {
    await fetch(`${API_URL}/documents`, {
      method: 'POST',
      headers: authHeaders(true),
      body: JSON.stringify({
        company_id: 1,
        document_type: 'invoice',
        supplier: 'NeuroAI Supplier',
        amount: Number(amount),
        vat_amount: Number(amount) * 0.23,
        currency: 'EUR',
        issue_date: new Date().toISOString().slice(0, 10),
        description
      })
    });

    setDescription('');
    setAmount('');

    loadData();
  }

  useEffect(() => {
    if (token) loadData().catch((e) => setError(e.message));
  }, [token]);

  if (!token) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.logo}>SEO NeuroAI</Text>
        <Text style={styles.subtitle}>Secure access</Text>
        <TextInput style={styles.input} placeholder='Email' placeholderTextColor='#94A3B8' autoCapitalize='none' value={email} onChangeText={setEmail} />
        <TextInput style={styles.input} placeholder='Password' placeholderTextColor='#94A3B8' secureTextEntry value={password} onChangeText={setPassword} />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <TouchableOpacity style={styles.button} onPress={login}><Text style={styles.buttonText}>Sign in</Text></TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <Text style={styles.logo}>SEO NeuroAI</Text>
        <Text style={styles.subtitle}>Operational Intelligence Infrastructure</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}

        <View style={styles.heroCard}>
          <Text style={styles.heroTitle}>Executive Dashboard</Text>

          <View style={styles.metricRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricValue}>€{dashboard?.total_expenses || 0}</Text>
              <Text style={styles.metricLabel}>Expenses</Text>
            </View>

            <View style={styles.metricBox}>
              <Text style={styles.metricValue}>{dashboard?.efficiency_score || 0}</Text>
              <Text style={styles.metricLabel}>Efficiency</Text>
            </View>
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>NeuroAI Insights</Text>

          <Text style={styles.insightText}>
            {insights?.neuro_ai_summary || 'Loading cognitive insights...'}
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Process Financial Document</Text>

          <TextInput
            style={styles.input}
            placeholder='Document description'
            placeholderTextColor='#94A3B8'
            value={description}
            onChangeText={setDescription}
          />

          <TextInput
            style={styles.input}
            placeholder='Amount'
            placeholderTextColor='#94A3B8'
            keyboardType='numeric'
            value={amount}
            onChangeText={setAmount}
          />

          <TouchableOpacity style={styles.button} onPress={createDocument}>
            <Text style={styles.buttonText}>Run NeuroAI</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Documents</Text>

          {documents.map((doc) => (
            <View key={doc.id} style={styles.documentCard}>
              <Text style={styles.documentSupplier}>{doc.supplier}</Text>
              <Text style={styles.documentText}>{doc.description}</Text>
              <Text style={styles.documentAmount}>€{doc.amount}</Text>
              <Text style={styles.documentCategory}>{doc.category}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#020617',
    padding: 20
  },
  logo: {
    color: '#FFFFFF',
    fontSize: 38,
    fontWeight: 'bold',
    marginTop: 20
  },
  subtitle: {
    color: '#94A3B8',
    marginBottom: 24,
    fontSize: 16
  },
  heroCard: {
    backgroundColor: '#0F172A',
    borderRadius: 24,
    padding: 24,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#1E293B'
  },
  heroTitle: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 18
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  metricBox: {
    backgroundColor: '#111827',
    borderRadius: 20,
    padding: 18,
    width: '48%'
  },
  metricValue: {
    color: '#10B981',
    fontSize: 28,
    fontWeight: 'bold'
  },
  metricLabel: {
    color: '#CBD5E1',
    marginTop: 6
  },
  card: {
    backgroundColor: '#0F172A',
    borderRadius: 24,
    padding: 22,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#1E293B'
  },
  sectionTitle: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 16
  },
  insightText: {
    color: '#CBD5E1',
    lineHeight: 22
  },
  error: {
    color: '#F87171',
    marginBottom: 14
  },
  input: {
    backgroundColor: '#111827',
    borderRadius: 16,
    padding: 16,
    color: '#FFFFFF',
    marginBottom: 14
  },
  button: {
    backgroundColor: '#10B981',
    borderRadius: 18,
    padding: 18,
    alignItems: 'center'
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: 'bold',
    fontSize: 16
  },
  documentCard: {
    backgroundColor: '#111827',
    borderRadius: 18,
    padding: 18,
    marginBottom: 14
  },
  documentSupplier: {
    color: '#FFFFFF',
    fontWeight: 'bold',
    fontSize: 16,
    marginBottom: 6
  },
  documentText: {
    color: '#CBD5E1'
  },
  documentAmount: {
    color: '#10B981',
    marginTop: 10,
    fontWeight: 'bold'
  },
  documentCategory: {
    color: '#60A5FA',
    marginTop: 6
  }
});
