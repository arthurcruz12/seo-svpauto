import React, { useMemo, useState } from 'react';
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';

const CORPUS = [
  { id: 1, text: 'motor completo bmw 320d n47 usado', family: 'Motor', brand: 'BMW', state: 'Usado', code: 'CUSA', unit: 'Picoto' },
  { id: 2, text: 'motor bmw serie 3 f30 diesel usado', family: 'Motor', brand: 'BMW', state: 'Usado', code: 'CUSA', unit: 'Picoto' },
  { id: 3, text: 'filtro oleo motor bmw 320d novo', family: 'Filtros', brand: 'BMW', state: 'Novo', code: 'CNOV', unit: 'Coimbra' },
  { id: 4, text: 'kit embraiagem volkswagen golf novo', family: 'Embraiagem', brand: 'Volkswagen', state: 'Novo', code: 'CNOV', unit: 'Coimbra' },
  { id: 5, text: 'caixa velocidades bmw f30 automatica usada', family: 'Caixa de velocidades', brand: 'BMW', state: 'Usado', code: 'CUSA', unit: 'Picoto' },
  { id: 6, text: 'pastilha travao frente audi a3 nova', family: 'Travagem', brand: 'Audi', state: 'Novo', code: 'CNOV', unit: 'Coimbra' },
  { id: 7, text: 'para choques traseiro mercedes classe c usado', family: 'Carroçaria', brand: 'Mercedes', state: 'Usado', code: 'CUSA', unit: 'Picoto' },
  { id: 8, text: 'bomba agua motor peugeot 308 nova', family: 'Arrefecimento', brand: 'Peugeot', state: 'Novo', code: 'CNOV', unit: 'Coimbra' },
];

const SAMPLE_INPUTS = [
  'MOTOR COMPLETO BMW 320 D US',
  'CX VEL BMW F30 AUT US',
  'FILTRO OLEO BMW 320D NOVO',
];

function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokenize(value) {
  const words = normalizeText(value).split(' ').filter(Boolean);
  const bigrams = [];
  for (let i = 0; i < words.length - 1; i += 1) {
    bigrams.push(`${words[i]}_${words[i + 1]}`);
  }
  return [...words, ...bigrams];
}

function countTokens(tokens) {
  return tokens.reduce((acc, token) => {
    acc[token] = (acc[token] || 0) + 1;
    return acc;
  }, {});
}

function tfidfVectors(documents) {
  const tokenized = documents.map(tokenize);
  const documentFrequency = {};

  tokenized.forEach((tokens) => {
    new Set(tokens).forEach((token) => {
      documentFrequency[token] = (documentFrequency[token] || 0) + 1;
    });
  });

  const totalDocuments = documents.length;

  return tokenized.map((tokens) => {
    const counts = countTokens(tokens);
    const totalTerms = Math.max(tokens.length, 1);
    const vector = {};

    Object.entries(counts).forEach(([token, count]) => {
      const tf = count / totalTerms;
      const idf = Math.log((1 + totalDocuments) / (1 + (documentFrequency[token] || 0))) + 1;
      vector[token] = tf * idf;
    });

    return vector;
  });
}

function cosineSimilarity(a, b) {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  let dot = 0;
  let normA = 0;
  let normB = 0;

  keys.forEach((key) => {
    const av = a[key] || 0;
    const bv = b[key] || 0;
    dot += av * bv;
    normA += av * av;
    normB += bv * bv;
  });

  if (!normA || !normB) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

function analyzeDescription(input) {
  const clean = normalizeText(input);
  if (!clean) return null;

  const docs = [...CORPUS.map((item) => item.text), clean];
  const vectors = tfidfVectors(docs);
  const queryVector = vectors[vectors.length - 1];

  const matches = CORPUS.map((item, index) => ({
    ...item,
    score: cosineSimilarity(queryVector, vectors[index]),
  }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  const best = matches[0];
  const confidence = Math.round(Math.min(99, Math.max(40, best.score * 112)));

  return {
    matches,
    confidence,
    best,
    vectorTerms: Object.entries(queryVector)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8),
  };
}

function Badge({ children, tone = 'green' }) {
  const toneStyle = tone === 'blue' ? styles.badgeBlue : tone === 'amber' ? styles.badgeAmber : styles.badgeGreen;
  return (
    <View style={[styles.badge, toneStyle]}>
      <Text style={styles.badgeText}>{children}</Text>
    </View>
  );
}

function Metric({ value, label, detail }) {
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricDetail}>{detail}</Text>
    </View>
  );
}

function NavButton({ label, active, onPress }) {
  return (
    <TouchableOpacity style={[styles.navButton, active && styles.navButtonActive]} onPress={onPress}>
      <Text style={[styles.navButtonText, active && styles.navButtonTextActive]}>{label}</Text>
    </TouchableOpacity>
  );
}

export default function App() {
  const [tab, setTab] = useState('assistant');
  const [description, setDescription] = useState('MOTOR COMPLETO BMW 320 D US');
  const [analysis, setAnalysis] = useState(() => analyzeDescription('MOTOR COMPLETO BMW 320 D US'));
  const [feedback, setFeedback] = useState('');

  const corpusStats = useMemo(() => {
    const allTerms = new Set(CORPUS.flatMap((item) => tokenize(item.text)));
    return { records: CORPUS.length, terms: allTerms.size };
  }, []);

  function runAnalysis() {
    setAnalysis(analyzeDescription(description));
    setFeedback('');
  }

  return (
    <SafeAreaView style={styles.page}>
      <View style={styles.shell}>
        <View style={styles.sidebar}>
          <View>
            <Text style={styles.brand}>SEO</Text>
            <Text style={styles.brandSub}>Sistema de Eficiência Operacional</Text>
          </View>

          <View style={styles.navGroup}>
            <NavButton label='Visão geral' active={tab === 'overview'} onPress={() => setTab('overview')} />
            <NavButton label='Assistente IA' active={tab === 'assistant'} onPress={() => setTab('assistant')} />
            <NavButton label='PLN / ML Lab' active={tab === 'lab'} onPress={() => setTab('lab')} />
            <NavButton label='Corpus' active={tab === 'corpus'} onPress={() => setTab('corpus')} />
          </View>

          <View style={styles.labBox}>
            <Text style={styles.labBoxTitle}>Shadow Mode</Text>
            <Text style={styles.labBoxText}>Motor isolado. Sem escrever no Atena ou no SEO de produção.</Text>
            <Badge>LAB ATIVO</Badge>
          </View>
        </View>

        <ScrollView style={styles.content} contentContainerStyle={styles.contentInner} showsVerticalScrollIndicator={false}>
          <View style={styles.topbar}>
            <View>
              <Text style={styles.eyebrow}>SEO INTELLIGENCE ENGINE</Text>
              <Text style={styles.pageTitle}>
                {tab === 'assistant' ? 'Assistente IA + Motor PLN' : tab === 'lab' ? 'Laboratório PLN / Machine Learning' : tab === 'corpus' ? 'Corpus operacional' : 'Visão geral'}
              </Text>
            </View>
            <View style={styles.statusWrap}>
              <View style={styles.statusDot} />
              <Text style={styles.statusText}>Preview seguro</Text>
            </View>
          </View>

          {tab === 'overview' && (
            <>
              <View style={styles.hero}>
                <View style={styles.heroCopy}>
                  <Text style={styles.heroTag}>NOVO MÓDULO</Text>
                  <Text style={styles.heroTitle}>A assistente agora consulta um motor semântico antes de sugerir uma classificação.</Text>
                  <Text style={styles.heroText}>Descrições de faturas → normalização → TF‑IDF → vetores → similaridade de cosseno → Top‑K → confiança → explicação da IA.</Text>
                </View>
              </View>

              <View style={styles.metricsRow}>
                <Metric value={`${corpusStats.records}`} label='Registos no corpus' detail='Amostra de demonstração' />
                <Metric value={`${corpusStats.terms}`} label='Features textuais' detail='Unigramas + bigramas' />
                <Metric value='Top‑3' label='Casos recuperados' detail='Similaridade de cosseno' />
                <Metric value='0' label='Escritas em produção' detail='Shadow Mode' />
              </View>

              <View style={styles.card}>
                <Text style={styles.cardTitle}>Fluxo integrado ao SEO</Text>
                <View style={styles.flowRow}>
                  {['OCR / IDP', 'Descrição', 'TF‑IDF', 'Cosseno', 'Classificação', 'Assistente IA'].map((item, index) => (
                    <React.Fragment key={item}>
                      <View style={styles.flowNode}><Text style={styles.flowText}>{item}</Text></View>
                      {index < 5 && <Text style={styles.arrow}>→</Text>}
                    </React.Fragment>
                  ))}
                </View>
              </View>
            </>
          )}

          {tab === 'assistant' && (
            <>
              <View style={styles.assistantGrid}>
                <View style={[styles.card, styles.assistantMain]}>
                  <View style={styles.cardHeaderRow}>
                    <View>
                      <Text style={styles.cardTitle}>Analisar descrição de fatura</Text>
                      <Text style={styles.cardSubtitle}>A assistente consulta o corpus antes de responder.</Text>
                    </View>
                    <Badge tone='blue'>TF‑IDF + COSINE</Badge>
                  </View>

                  <TextInput
                    style={styles.input}
                    value={description}
                    onChangeText={setDescription}
                    placeholder='Ex.: CX VEL BMW F30 AUT US'
                    placeholderTextColor='#64748B'
                  />

                  <View style={styles.samplesRow}>
                    {SAMPLE_INPUTS.map((sample) => (
                      <TouchableOpacity key={sample} style={styles.sampleButton} onPress={() => { setDescription(sample); setAnalysis(analyzeDescription(sample)); setFeedback(''); }}>
                        <Text style={styles.sampleText}>{sample}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>

                  <TouchableOpacity style={styles.primaryButton} onPress={runAnalysis}>
                    <Text style={styles.primaryButtonText}>Executar motor PLN</Text>
                  </TouchableOpacity>

                  {analysis && (
                    <View style={styles.aiAnswer}>
                      <View style={styles.aiHeader}>
                        <View style={styles.aiIcon}><Text style={styles.aiIconText}>AI</Text></View>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.aiTitle}>Assistente SEO</Text>
                          <Text style={styles.aiMeta}>Resposta apoiada pelo histórico operacional</Text>
                        </View>
                        <Badge tone={analysis.confidence >= 80 ? 'green' : 'amber'}>{analysis.confidence}% confiança</Badge>
                      </View>

                      <Text style={styles.answerLead}>Classificação mais provável</Text>
                      <Text style={styles.answerPrediction}>{analysis.best.family} · {analysis.best.brand} · {analysis.best.state}</Text>

                      <View style={styles.classificationRow}>
                        <View style={styles.classificationCell}><Text style={styles.cellLabel}>Código</Text><Text style={styles.cellValue}>{analysis.best.code}</Text></View>
                        <View style={styles.classificationCell}><Text style={styles.cellLabel}>Unidade provável</Text><Text style={styles.cellValue}>{analysis.best.unit}</Text></View>
                        <View style={styles.classificationCell}><Text style={styles.cellLabel}>Método</Text><Text style={styles.cellValue}>Top‑K semântico</Text></View>
                      </View>

                      <Text style={styles.explanation}>Encontrei descrições historicamente semelhantes no corpus. A sugestão é apresentada para revisão humana e não altera o Atena nem o SEO principal.</Text>

                      <View style={styles.feedbackRow}>
                        <TouchableOpacity style={styles.feedbackPositive} onPress={() => setFeedback('Classificação confirmada — este exemplo seria adicionado ao corpus validado.')}> 
                          <Text style={styles.feedbackPositiveText}>✓ Confirmar</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.feedbackNeutral} onPress={() => setFeedback('Correção solicitada — a revisão humana alimentaria o próximo re-treino.')}> 
                          <Text style={styles.feedbackNeutralText}>Corrigir</Text>
                        </TouchableOpacity>
                      </View>
                      {feedback ? <Text style={styles.feedbackMessage}>{feedback}</Text> : null}
                    </View>
                  )}
                </View>

                <View style={[styles.card, styles.assistantSide]}>
                  <Text style={styles.cardTitle}>Top correspondências</Text>
                  <Text style={styles.cardSubtitle}>Similaridade de cosseno contra o corpus.</Text>
                  {analysis?.matches.map((match, index) => (
                    <View key={match.id} style={styles.matchCard}>
                      <View style={styles.matchHeader}>
                        <Text style={styles.matchRank}>#{index + 1}</Text>
                        <Text style={styles.matchScore}>{Math.round(match.score * 100)}%</Text>
                      </View>
                      <Text style={styles.matchText}>{match.text}</Text>
                      <Text style={styles.matchMeta}>{match.family} · {match.code} · {match.unit}</Text>
                      <View style={styles.progressTrack}><View style={[styles.progressFill, { width: `${Math.max(4, Math.round(match.score * 100))}%` }]} /></View>
                    </View>
                  ))}
                </View>
              </View>
            </>
          )}

          {tab === 'lab' && (
            <>
              <View style={styles.metricsRow}>
                <Metric value='TF‑IDF' label='Vetorização' detail='Peso por relevância textual' />
                <Metric value='Cosine' label='Similaridade' detail='Proximidade entre vetores' />
                <Metric value='(1,2)' label='N-grams' detail='Palavras + expressões' />
                <Metric value='HITL' label='Feedback' detail='Human-in-the-loop' />
              </View>

              <View style={styles.twoCol}>
                <View style={[styles.card, styles.flexCard]}>
                  <Text style={styles.cardTitle}>Pipeline do motor</Text>
                  {[
                    ['01', 'Normalização', 'Lowercase, acentos, ruído e abreviações.'],
                    ['02', 'Tokenização', 'Unigramas e bigramas do vocabulário operacional.'],
                    ['03', 'TF‑IDF', 'Cada termo vira uma coordenada com peso matemático.'],
                    ['04', 'Cosine', 'Compara o novo vetor aos vetores históricos.'],
                    ['05', 'Top‑K + confiança', 'Recupera casos próximos e produz uma sugestão explicável.'],
                    ['06', 'Feedback humano', 'Confirmações e correções entram no corpus validado.'],
                  ].map(([step, title, text]) => (
                    <View style={styles.pipelineItem} key={step}>
                      <View style={styles.stepCircle}><Text style={styles.stepText}>{step}</Text></View>
                      <View style={{ flex: 1 }}><Text style={styles.pipelineTitle}>{title}</Text><Text style={styles.pipelineText}>{text}</Text></View>
                    </View>
                  ))}
                </View>

                <View style={[styles.card, styles.flexCard]}>
                  <Text style={styles.cardTitle}>Vetor da descrição atual</Text>
                  <Text style={styles.cardSubtitle}>Features com maior peso TF‑IDF nesta execução.</Text>
                  {analysis?.vectorTerms.map(([term, weight], index) => (
                    <View key={term} style={styles.vectorRow}>
                      <Text style={styles.vectorTerm}>{term.replace('_', ' ')}</Text>
                      <View style={styles.vectorTrack}><View style={[styles.vectorFill, { width: `${Math.min(100, 30 + weight * 180)}%` }]} /></View>
                      <Text style={styles.vectorWeight}>{weight.toFixed(3)}</Text>
                    </View>
                  ))}
                </View>
              </View>

              <View style={styles.noticeCard}>
                <Text style={styles.noticeTitle}>Arquitetura de produção proposta</Text>
                <Text style={styles.noticeText}>No backend real, este módulo passa para Python + scikit-learn (`TfidfVectorizer`, `cosine_similarity` e classificador supervisionado). O preview mantém a lógica isolada no cliente apenas para validar UX, regras e explicabilidade.</Text>
              </View>
            </>
          )}

          {tab === 'corpus' && (
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <View>
                  <Text style={styles.cardTitle}>Corpus de treino — demonstração</Text>
                  <Text style={styles.cardSubtitle}>Cada descrição histórica carrega contexto operacional validado.</Text>
                </View>
                <Badge>{CORPUS.length} REGISTOS</Badge>
              </View>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <View style={{ minWidth: 850 }}>
                  <View style={styles.tableHeader}>
                    <Text style={[styles.th, { flex: 2.6 }]}>Descrição</Text>
                    <Text style={styles.th}>Família</Text>
                    <Text style={styles.th}>Marca</Text>
                    <Text style={styles.th}>Estado</Text>
                    <Text style={styles.th}>Código</Text>
                    <Text style={styles.th}>Unidade</Text>
                  </View>
                  {CORPUS.map((item) => (
                    <View style={styles.tableRow} key={item.id}>
                      <Text style={[styles.td, { flex: 2.6 }]}>{item.text}</Text>
                      <Text style={styles.td}>{item.family}</Text>
                      <Text style={styles.td}>{item.brand}</Text>
                      <Text style={styles.td}>{item.state}</Text>
                      <Text style={styles.td}>{item.code}</Text>
                      <Text style={styles.td}>{item.unit}</Text>
                    </View>
                  ))}
                </View>
              </ScrollView>
            </View>
          )}

          <Text style={styles.footer}>SEO Intelligence Engine · Preview isolado · Nenhuma integração em produção</Text>
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#07110D' },
  shell: { flex: 1, flexDirection: 'row', minHeight: '100vh' },
  sidebar: { width: 245, backgroundColor: '#0A1712', borderRightWidth: 1, borderRightColor: '#163226', padding: 24, justifyContent: 'space-between' },
  brand: { color: '#E8FFF3', fontSize: 31, fontWeight: '800', letterSpacing: 1.5 },
  brandSub: { color: '#6F9682', fontSize: 11, lineHeight: 16, marginTop: 3 },
  navGroup: { gap: 8, marginTop: 34, flex: 1 },
  navButton: { paddingVertical: 13, paddingHorizontal: 14, borderRadius: 12 },
  navButtonActive: { backgroundColor: '#143326' },
  navButtonText: { color: '#789485', fontSize: 14, fontWeight: '600' },
  navButtonTextActive: { color: '#DFFFF0' },
  labBox: { backgroundColor: '#0E241A', borderWidth: 1, borderColor: '#1C4933', borderRadius: 16, padding: 14 },
  labBoxTitle: { color: '#B6F6D2', fontSize: 13, fontWeight: '800', marginBottom: 5 },
  labBoxText: { color: '#729583', fontSize: 11, lineHeight: 16, marginBottom: 10 },
  content: { flex: 1, backgroundColor: '#09130F' },
  contentInner: { padding: 32, maxWidth: 1450, width: '100%', alignSelf: 'center' },
  topbar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 26 },
  eyebrow: { color: '#48D98A', fontSize: 11, fontWeight: '800', letterSpacing: 1.8, marginBottom: 7 },
  pageTitle: { color: '#F2FFF8', fontSize: 28, fontWeight: '800' },
  statusWrap: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#0F2118', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, borderWidth: 1, borderColor: '#1A3B2A' },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#46E38D', marginRight: 8 },
  statusText: { color: '#9BC6AF', fontSize: 12, fontWeight: '700' },
  hero: { backgroundColor: '#0D2017', borderRadius: 22, borderWidth: 1, borderColor: '#1B432F', padding: 30, marginBottom: 20 },
  heroCopy: { maxWidth: 900 },
  heroTag: { color: '#4CE593', fontSize: 11, fontWeight: '900', letterSpacing: 1.5, marginBottom: 10 },
  heroTitle: { color: '#F0FFF7', fontSize: 27, lineHeight: 35, fontWeight: '800' },
  heroText: { color: '#8FB39F', fontSize: 14, lineHeight: 22, marginTop: 12 },
  metricsRow: { flexDirection: 'row', gap: 12, flexWrap: 'wrap', marginBottom: 20 },
  metricCard: { minWidth: 180, flex: 1, backgroundColor: '#0D1D16', borderRadius: 18, padding: 18, borderWidth: 1, borderColor: '#173728' },
  metricValue: { color: '#57E99B', fontSize: 25, fontWeight: '800' },
  metricLabel: { color: '#D9F3E5', fontSize: 12, fontWeight: '700', marginTop: 5 },
  metricDetail: { color: '#638270', fontSize: 10, marginTop: 4 },
  card: { backgroundColor: '#0D1D16', borderRadius: 20, padding: 22, borderWidth: 1, borderColor: '#173728', marginBottom: 18 },
  cardHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 },
  cardTitle: { color: '#EDFFF5', fontSize: 18, fontWeight: '800', marginBottom: 5 },
  cardSubtitle: { color: '#6F917F', fontSize: 12, lineHeight: 18, marginBottom: 16 },
  flowRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  flowNode: { paddingHorizontal: 14, paddingVertical: 11, backgroundColor: '#112B1E', borderRadius: 12, borderWidth: 1, borderColor: '#20553A' },
  flowText: { color: '#BCECD1', fontSize: 12, fontWeight: '700' },
  arrow: { color: '#3F6B52', fontSize: 18 },
  badge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, alignSelf: 'flex-start' },
  badgeGreen: { backgroundColor: '#123923', borderWidth: 1, borderColor: '#256743' },
  badgeBlue: { backgroundColor: '#12293A', borderWidth: 1, borderColor: '#22577B' },
  badgeAmber: { backgroundColor: '#3A2B12', borderWidth: 1, borderColor: '#755520' },
  badgeText: { color: '#D9FFEA', fontSize: 9, fontWeight: '900', letterSpacing: 0.7 },
  assistantGrid: { flexDirection: 'row', gap: 18, alignItems: 'flex-start', flexWrap: 'wrap' },
  assistantMain: { flex: 2, minWidth: 520 },
  assistantSide: { flex: 1, minWidth: 300 },
  input: { backgroundColor: '#08140E', color: '#E8FFF2', borderWidth: 1, borderColor: '#1B432F', borderRadius: 14, padding: 15, fontSize: 14, marginTop: 6, marginBottom: 10 },
  samplesRow: { flexDirection: 'row', gap: 7, flexWrap: 'wrap', marginBottom: 13 },
  sampleButton: { backgroundColor: '#10251A', borderWidth: 1, borderColor: '#1A3D2B', paddingHorizontal: 10, paddingVertical: 7, borderRadius: 10 },
  sampleText: { color: '#789B87', fontSize: 9, fontWeight: '700' },
  primaryButton: { backgroundColor: '#32D67D', borderRadius: 13, paddingVertical: 14, alignItems: 'center', marginBottom: 18 },
  primaryButtonText: { color: '#052314', fontSize: 13, fontWeight: '900' },
  aiAnswer: { backgroundColor: '#0A1711', borderRadius: 17, borderWidth: 1, borderColor: '#205039', padding: 18 },
  aiHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 17 },
  aiIcon: { width: 36, height: 36, borderRadius: 12, backgroundColor: '#174B31', alignItems: 'center', justifyContent: 'center' },
  aiIconText: { color: '#75F0AA', fontWeight: '900', fontSize: 11 },
  aiTitle: { color: '#EFFFF6', fontSize: 13, fontWeight: '800' },
  aiMeta: { color: '#628270', fontSize: 9, marginTop: 2 },
  answerLead: { color: '#759682', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 },
  answerPrediction: { color: '#F1FFF7', fontSize: 20, fontWeight: '800', marginTop: 5, marginBottom: 13 },
  classificationRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap', marginBottom: 12 },
  classificationCell: { minWidth: 120, flex: 1, backgroundColor: '#0E2117', borderRadius: 11, padding: 11, borderWidth: 1, borderColor: '#163B29' },
  cellLabel: { color: '#668271', fontSize: 9, marginBottom: 4 },
  cellValue: { color: '#CFF6DF', fontSize: 12, fontWeight: '800' },
  explanation: { color: '#88A796', fontSize: 11, lineHeight: 17, marginBottom: 14 },
  feedbackRow: { flexDirection: 'row', gap: 8 },
  feedbackPositive: { flex: 1, backgroundColor: '#143B25', padding: 11, borderRadius: 10, alignItems: 'center' },
  feedbackPositiveText: { color: '#7BF0AC', fontSize: 11, fontWeight: '800' },
  feedbackNeutral: { flex: 1, backgroundColor: '#14221A', padding: 11, borderRadius: 10, alignItems: 'center', borderWidth: 1, borderColor: '#294536' },
  feedbackNeutralText: { color: '#AAC2B5', fontSize: 11, fontWeight: '800' },
  feedbackMessage: { color: '#7DEFAE', fontSize: 10, marginTop: 10, lineHeight: 15 },
  matchCard: { backgroundColor: '#0A1711', borderRadius: 14, padding: 13, borderWidth: 1, borderColor: '#173526', marginBottom: 9 },
  matchHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 7 },
  matchRank: { color: '#50735F', fontSize: 10, fontWeight: '800' },
  matchScore: { color: '#5AE99D', fontSize: 12, fontWeight: '900' },
  matchText: { color: '#DDF9E9', fontSize: 11, fontWeight: '700', lineHeight: 17 },
  matchMeta: { color: '#637F6F', fontSize: 9, marginTop: 5 },
  progressTrack: { height: 4, backgroundColor: '#14261B', borderRadius: 3, overflow: 'hidden', marginTop: 10 },
  progressFill: { height: 4, backgroundColor: '#3EDB84', borderRadius: 3 },
  twoCol: { flexDirection: 'row', gap: 18, alignItems: 'stretch', flexWrap: 'wrap' },
  flexCard: { flex: 1, minWidth: 370 },
  pipelineItem: { flexDirection: 'row', gap: 12, marginTop: 13, alignItems: 'flex-start' },
  stepCircle: { width: 35, height: 35, borderRadius: 10, backgroundColor: '#143823', alignItems: 'center', justifyContent: 'center' },
  stepText: { color: '#5DEB9F', fontSize: 9, fontWeight: '900' },
  pipelineTitle: { color: '#DCF7E8', fontSize: 12, fontWeight: '800' },
  pipelineText: { color: '#6F8B7A', fontSize: 10, lineHeight: 15, marginTop: 3 },
  vectorRow: { flexDirection: 'row', alignItems: 'center', gap: 9, marginTop: 12 },
  vectorTerm: { color: '#C8E8D7', fontSize: 10, width: 100 },
  vectorTrack: { flex: 1, height: 7, backgroundColor: '#13261B', borderRadius: 5, overflow: 'hidden' },
  vectorFill: { height: 7, backgroundColor: '#38D982', borderRadius: 5 },
  vectorWeight: { color: '#638572', width: 45, fontSize: 9, textAlign: 'right' },
  noticeCard: { backgroundColor: '#102418', borderWidth: 1, borderColor: '#285E40', borderRadius: 18, padding: 18, marginBottom: 18 },
  noticeTitle: { color: '#B9F4D1', fontSize: 13, fontWeight: '800', marginBottom: 6 },
  noticeText: { color: '#789A87', fontSize: 11, lineHeight: 18 },
  tableHeader: { flexDirection: 'row', paddingVertical: 11, borderBottomWidth: 1, borderBottomColor: '#21432F' },
  tableRow: { flexDirection: 'row', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#142C20' },
  th: { flex: 1, color: '#648170', fontSize: 9, fontWeight: '800', textTransform: 'uppercase' },
  td: { flex: 1, color: '#BBD8C8', fontSize: 10, paddingRight: 12 },
  footer: { color: '#365344', fontSize: 9, textAlign: 'center', marginTop: 8, marginBottom: 24 },
});
