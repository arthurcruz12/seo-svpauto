import React, { useEffect, useState } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput
} from 'react-native';

const API_URL = 'http://127.0.0.1:8000';

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');

  async function loadDashboard() {
    try {
      const response = await fetch(`${API_URL}/dashboard/1`);
      const data = await response.json();
      setDashboard(data);
    } catch (error) {
      console.log(error);
    }
  }

  async function loadDocuments() {
    try {
      const response = await fetch(`${API_URL}/documents`);
      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.log(error);
    }
  }

  async function createDocument() {
    try {
      await fetch(`${API_URL}/documents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          company_id: 1,
          document_type: 'invoice',
          supplier: 'Fornecedor NeuroAI',
          amount: Number(amount),
          vat_amount: Number(amount) * 0.23,
          currency: 'EUR',
          issue_date: '2026-05-27',
          description: description
        })
      });

      setDescription('');
      setAmount('');

      loadDocuments();
      loadDashboard();
    } catch (error) {
      console.log(error);
    }
  }

  useEffect(() => {
    loadDashboard();
    loadDocuments();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <Text style={styles.title}>SEO NeuroAI</Text>
        <Text style={styles.subtitle}>AI Backoffice</Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Dashboard Executivo</Text>

          <Text style={styles.metric}>
            Despesas Totais: €{dashboard?.total_expenses || 0}
          </Text>

          <Text style={styles.metric}>
            Eficiência Operacional: {dashboard?.efficiency_score || 0}
          </Text>

          <Text style={styles.metric}>
            Documentos: {dashboard?.documents || 0}
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Adicionar Documento</Text>

          <TextInput
            style={styles.input}
            placeholder='Descrição'
            value={description}
            onChangeText={setDescription}
          />

          <TextInput
            style={styles.input}
            placeholder='Valor'
            keyboardType='numeric'
            value={amount}
            onChangeText={setAmount}
          />

          <TouchableOpacity style={styles.button} onPress={createDocument}>
            <Text style={styles.buttonText}>Processar com NeuroAI</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Documentos</Text>

          {documents.map((doc) => (
            <View key={doc.id} style={styles.documentItem}>
              <Text style={styles.documentTitle}>{doc.supplier}</Text>
              <Text>{doc.description}</Text>
              <Text>€{doc.amount}</Text>
              <Text>{doc.category}</Text>
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
    backgroundColor: '#0F172A',
    padding: 20
  },
  title: {
    color: '#FFFFFF',
    fontSize: 34,
    fontWeight: 'bold',
    marginTop: 20
  },
  subtitle: {
    color: '#94A3B8',
    fontSize: 18,
    marginBottom: 20
  },
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 20,
    padding: 20,
    marginBottom: 20
  },
  cardTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15
  },
  metric: {
    color: '#E2E8F0',
    fontSize: 16,
    marginBottom: 10
  },
  input: {
    backgroundColor: '#334155',
    borderRadius: 12,
    padding: 14,
    color: '#FFFFFF',
    marginBottom: 12
  },
  button: {
    backgroundColor: '#10B981',
    borderRadius: 14,
    padding: 16,
    alignItems: 'center'
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: 'bold'
  },
  documentItem: {
    backgroundColor: '#334155',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10
  },
  documentTitle: {
    color: '#FFFFFF',
    fontWeight: 'bold',
    marginBottom: 4
  }
});
