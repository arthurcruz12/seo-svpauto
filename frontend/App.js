import React, { useEffect, useState } from 'react';
import { SafeAreaView, View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput } from 'react-native';

const API_URL = 'http://127.0.0.1:8000';

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [insights, setInsights] = useState(null);
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');

  async function loadData() {
    const dashboardResponse = await fetch(`${API_URL}/dashboard/1`);
    const dashboardData = await dashboardResponse.json();
    setDashboard(dashboardData);

    const documentsResponse = await fetch(`${API_URL}/documents`);
    const documentsData = await documentsResponse.json();
    setDocuments(documentsData);

    const insightsResponse = await fetch(`${API_URL}/companies/1/neuro-insights`);
    const insightsData = await insightsResponse.json();
    setInsights(insightsData);
  }

  async function createDocument() {
    await fetch(`${API_URL}/documents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        company_id: 1,
        document_type: 'invoice',
        supplier: 'NeuroAI Supplier',
        amount: Number(amount),
        vat_amount: Number(amount) * 0.23,
        currency: 'EUR',
        issue_date: '2026-05-28',
        description
      })
    });

    setDescription('');
    setAmount('');

    loadData();
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <Text style={styles.logo}>SEO NeuroAI</Text>
        <Text style={styles.subtitle}>Operational Intelligence Infrastructure</Text>

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
