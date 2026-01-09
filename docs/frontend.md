# Frontend Specification - Real-Time Malware Detection Gateway

## Vue 3 + Vite + TypeScript Frontend Documentation

This document describes all requirements and specifications for building a Vue 3 + Vite + TypeScript frontend to interface with the Real-Time Malware Detection Gateway FastAPI backend.

---

## 1. Project Overview

The frontend provides a web-based dashboard and interface for:
- **Scanning URLs and files** for malware detection
- **Monitoring threat logs** with real-time updates
- **Viewing system health** and statistics
- **Managing detection thresholds** and settings
- **Visualizing threat data** through charts and graphs

---

## 2. Technology Stack

### Core Dependencies

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.5",
    "pinia": "^2.1.7",
    "axios": "^1.6.0",
    "chart.js": "^4.4.0",
    "vue-chartjs": "^5.3.0",
    "date-fns": "^3.0.0",
    "lodash-es": "^4.17.21"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "vue-tsc": "^1.8.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "@types/lodash-es": "^4.17.12"
  }
}
```

### Recommended Additional Libraries

| Library | Purpose |
|---------|---------|
| `axios` | HTTP client for API calls |
| `chart.js` + `vue-chartjs` | Charts and visualizations |
| `date-fns` | Date formatting and manipulation |
| `lodash-es` | Utility functions |
| `vueuse` | Vue composition utilities |
| `@headlessui/vue` | Accessible UI components |
| `@heroicons/vue` | Icon set |
| `pinia-plugin-persistedstate` | State persistence |

---

## 3. API Integration

### Base Configuration

```typescript
// src/config/api.ts
interface ApiConfig {
  baseURL: string;
  timeout: number;
  headers: Record<string, string>;
}

export const apiConfig: ApiConfig = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
};
```

### API Client Setup

```typescript
// src/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';
import { apiConfig } from '@/config/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create(apiConfig);
    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  get<T>(url: string, params?: object): Promise<T> {
    return this.client.get(url, { params }).then((r) => r.data);
  }

  post<T>(url: string, data?: object): Promise<T> {
    return this.client.post(url, data).then((r) => r.data);
  }

  put<T>(url: string, data?: object): Promise<T> {
    return this.client.put(url, data).then((r) => r.data);
  }

  delete<T>(url: string): Promise<T> {
    return this.client.delete(url).then((r) => r.data);
  }
}

export const api = new ApiClient();
```

---

## 4. TypeScript Data Models

### Enums

```typescript
// src/types/enums.ts
export enum RiskLevel {
  BENIGN = 'BENIGN',
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum SourceType {
  URL = 'URL',
  FILE = 'FILE',
}

export enum ScanStatus {
  CLEAN = 'CLEAN',
  THREAT_DETECTED = 'THREAT_DETECTED',
  ERROR = 'ERROR',
  PENDING = 'PENDING',
}
```

### Request Models

```typescript
// src/types/requests.ts
import { HttpUrl } from 'pydantic'; // Use custom type or string

export interface UrlScanRequest {
  url: string;
  block_on_detection: boolean;
}

export interface FileScanRequest {
  filename?: string;
  block_on_detection: boolean;
}

export interface ThresholdUpdateRequest {
  threshold: number; // 0.0 to 1.0
}

export interface PaginationParams {
  limit: number;
  offset: number;
  risk_level?: string;
  source_type?: string;
}
```

### Response Models

```typescript
// src/types/responses.ts
import { RiskLevel, SourceType, ScanStatus } from './enums';

export interface ModelStatus {
  loaded: boolean;
  model_path: string;
  device: string;
  parameters?: number;
  vocab_size: number;
  d_model: number;
  num_layers: number;
}

export interface DatabaseStatus {
  connected: boolean;
  path: string;
  total_threats: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  model: ModelStatus;
  database: DatabaseStatus;
  uptime_seconds: number;
  memory_usage_mb: number;
  timestamp: string;
}

export interface ScanResult {
  source: string;
  source_type: SourceType;
  probability: number;
  risk_level: RiskLevel;
  bytes_scanned: number;
  blocked: boolean;
  scan_time_ms: number;
  status: ScanStatus;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface ThreatLog {
  id: number;
  source: string;
  source_type: SourceType;
  probability: number;
  bytes_scanned: number;
  risk_level: RiskLevel;
  timestamp: string;
  details?: string;
  blocked: boolean;
}

export interface ThreatListResponse {
  threats: ThreatLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface ThreatStats {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  benign: number;
  total_bytes_scanned: number;
}

export interface RiskDistribution {
  BENIGN: number;
  LOW: number;
  MEDIUM: number;
  HIGH: number;
  CRITICAL: number;
}

export interface SettingsStatus {
  confidence_threshold: number;
  chunk_size: number;
  window_size: number;
  temperature: number;
  risk_levels: Record<string, [number, number]>;
}

export interface ThresholdResponse {
  old_threshold: number;
  new_threshold: number;
  status: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface RootResponse {
  name: string;
  version: string;
  status: string;
  endpoints: Record<string, string>;
}
```

### Stats Response

```typescript
// src/types/stats.ts
export interface DetectorStats {
  total_scans: number;
  threats_detected: number;
  bytes_scanned: number;
  avg_scan_time_ms: number;
  last_scan_time?: string;
}

export interface ThreatManagerStats {
  total_threats: number;
  threats_by_level: Record<string, number>;
}

export interface FullStatsResponse {
  detector: DetectorStats;
  threat_manager: ThreatManagerStats;
  uptime_seconds: number;
}
```

---

## 5. API Endpoints Reference

### Health & Status Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/health` | System health check | None | [`HealthStatus`](#healthstatus) |
| GET | `/settings` | Get current settings | None | [`SettingsStatus`](#settingsstatus) |
| GET | `/` | Root endpoint with API info | None | [`RootResponse`](#rootresponse) |

### Scanning Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/scan/url` | Scan a URL for malware | [`UrlScanRequest`](#urlscanrequest) | [`ScanResult`](#scanresult) |
| POST | `/scan/file` | Upload and scan a file | `multipart/form-data` | [`ScanResult`](#scanresult) |

### Threat Management Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/threats` | Get threat logs with pagination | Query params | [`ThreatListResponse`](#threatlistresponse) |
| GET | `/threats/stats` | Get aggregated threat stats | None | [`ThreatStats`](#threatstats) |
| GET | `/threats/distribution` | Get threat distribution by level | None | [`RiskDistribution`](#riskdistribution) |
| GET | `/threats/{id}` | Get specific threat by ID | Path param: `id` | [`ThreatLog`](#threatlog) |

### Settings Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/settings/threshold` | Update detection threshold | [`ThresholdUpdateRequest`](#thresholdupdaterequest) | [`ThresholdResponse`](#thresholdresponse) |

### Statistics Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/stats` | Get detector and system stats | None | [`FullStatsResponse`](#fullstatsresponse) |

---

## 6. Vue Components Architecture

### Component Hierarchy

```
src/
├── components/
│   ├── common/
│   │   ├── Button.vue
│   │   ├── Card.vue
│   │   ├── Modal.vue
│   │   ├── Badge.vue
│   │   ├── LoadingSpinner.vue
│   │   └── EmptyState.vue
│   │
│   ├── layout/
│   │   ├── Navbar.vue
│   │   ├── Sidebar.vue
│   │   ├── Header.vue
│   │   └── Footer.vue
│   │
│   ├── dashboard/
│   │   ├── StatsCard.vue
│   │   ├── ThreatChart.vue
│   │   ├── RecentThreats.vue
│   │   ├── SystemHealth.vue
│   │   └── QuickActions.vue
│   │
│   ├── scanner/
│   │   ├── UrlScanner.vue
│   │   ├── FileUploader.vue
│   │   ├── ScanProgress.vue
│   │   └── ScanResult.vue
│   │
│   ├── threats/
│   │   ├── ThreatTable.vue
│   │   ├── ThreatFilters.vue
│   │   ├── ThreatDetail.vue
│   │   └── ThreatStats.vue
│   │
│   └── settings/
│       ├── ThresholdSlider.vue
│       ├── SettingsForm.vue
│       └── ConfigurationPanel.vue
│
├── views/
│   ├── DashboardView.vue
│   ├── ScannerView.vue
│   ├── ThreatsView.vue
│   ├── SettingsView.vue
│   └── NotFoundView.vue
│
├── stores/
│   ├── auth.ts
│   ├── scan.ts
│   ├── threats.ts
│   ├── settings.ts
│   └── stats.ts
│
├── composables/
│   ├── useApi.ts
│   ├── useScan.ts
│   ├── useThreats.ts
│   └── usePolling.ts
│
├── router/
│   └── index.ts
│
├── types/
│   ├── enums.ts
│   ├── requests.ts
│   ├── responses.ts
│   └── stats.ts
│
├── api/
│   ├── client.ts
│   ├── health.ts
│   ├── scanner.ts
│   ├── threats.ts
│   └── settings.ts
│
└── App.vue
```

---

## 7. Pinia Stores

### Scan Store

```typescript
// src/stores/scan.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '@/api/client';
import type { ScanResult, UrlScanRequest, SourceType } from '@/types';

export const useScanStore = defineStore('scan', () => {
  // State
  const currentScan = ref<ScanResult | null>(null);
  const scanHistory = ref<ScanResult[]>([]);
  const isScanning = ref(false);
  const scanError = ref<string | null>(null);

  // Getters
  const hasActiveScan = computed(() => isScanning.value);
  const lastScan = computed(() => scanHistory.value[0] || null);
  const threatsDetected = computed(() => 
    scanHistory.value.filter(s => s.blocked)
  );

  // Actions
  async function scanUrl(request: UrlScanRequest): Promise<ScanResult> {
    isScanning.value = true;
    scanError.value = null;
    
    try {
      const result = await api.post<ScanResult>('/scan/url', request);
      currentScan.value = result;
      scanHistory.value.unshift(result);
      return result;
    } catch (error) {
      scanError.value = error instanceof Error ? error.message : 'Unknown error';
      throw error;
    } finally {
      isScanning.value = false;
    }
  }

  async function scanFile(file: File, blockOnDetection = true): Promise<ScanResult> {
    isScanning.value = true;
    scanError.value = null;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('block_on_detection', blockOnDetection.toString());
    
    try {
      const result = await api.post<ScanResult>('/scan/file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      currentScan.value = result;
      scanHistory.value.unshift(result);
      return result;
    } catch (error) {
      scanError.value = error instanceof Error ? error.message : 'Unknown error';
      throw error;
    } finally {
      isScanning.value = false;
    }
  }

  function clearCurrentScan(): void {
    currentScan.value = null;
    scanError.value = null;
  }

  function clearHistory(): void {
    scanHistory.value = [];
  }

  return {
    currentScan,
    scanHistory,
    isScanning,
    scanError,
    hasActiveScan,
    lastScan,
    threatsDetected,
    scanUrl,
    scanFile,
    clearCurrentScan,
    clearHistory,
  };
});
```

### Threats Store

```typescript
// src/stores/threats.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '@/api/client';
import type { ThreatListResponse, ThreatLog, ThreatStats, RiskDistribution } from '@/types';

export const useThreatsStore = defineStore('threats', () => {
  // State
  const threats = ref<ThreatLog[]>([]);
  const totalCount = ref(0);
  const currentStats = ref<ThreatStats | null>(null);
  const distribution = ref<RiskDistribution | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const filters = ref({
    limit: 100,
    offset: 0,
    risk_level: undefined as string | undefined,
    source_type: undefined as string | undefined,
  });

  // Getters
  const criticalThreats = computed(() => 
    threats.value.filter(t => t.risk_level === 'CRITICAL')
  );
  
  const highThreats = computed(() => 
    threats.value.filter(t => t.risk_level === 'HIGH')
  );

  const hasThreats = computed(() => threats.value.length > 0);

  // Actions
  async function fetchThreats(): Promise<void> {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await api.get<ThreatListResponse>('/threats', filters.value);
      threats.value = response.threats;
      totalCount.value = response.total;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch threats';
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchStats(): Promise<void> {
    try {
      const stats = await api.get<ThreatStats>('/threats/stats');
      currentStats.value = stats;
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  }

  async function fetchDistribution(): Promise<void> {
    try {
      const dist = await api.get<RiskDistribution>('/threats/distribution');
      distribution.value = dist;
    } catch (e) {
      console.error('Failed to fetch distribution:', e);
    }
  }

  async function fetchThreatById(id: number): Promise<ThreatLog | null> {
    try {
      return await api.get<ThreatLog>(`/threats/${id}`);
    } catch (e) {
      console.error('Failed to fetch threat:', e);
      return null;
    }
  }

  function updateFilters(newFilters: Partial<typeof filters.value>): void {
    filters.value = { ...filters.value, ...newFilters };
    fetchThreats();
  }

  function setPage(offset: number): void {
    filters.value.offset = offset;
    fetchThreats();
  }

  function setLimit(limit: number): void {
    filters.value.limit = limit;
    filters.value.offset = 0;
    fetchThreats();
  }

  return {
    threats,
    totalCount,
    currentStats,
    distribution,
    isLoading,
    error,
    filters,
    criticalThreats,
    highThreats,
    hasThreats,
    fetchThreats,
    fetchStats,
    fetchDistribution,
    fetchThreatById,
    updateFilters,
    setPage,
    setLimit,
  };
});
```

### Settings Store

```typescript
// src/stores/settings.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api/client';
import type { SettingsStatus, ThresholdResponse } from '@/types';

export const useSettingsStore = defineStore('settings', () => {
  // State
  const settings = ref<SettingsStatus | null>(null);
  const isUpdating = ref(false);
  const updateError = ref<string | null>(null);

  // Actions
  async function fetchSettings(): Promise<void> {
    try {
      settings.value = await api.get<SettingsStatus>('/settings');
    } catch (e) {
      console.error('Failed to fetch settings:', e);
    }
  }

  async function updateThreshold(threshold: number): Promise<ThresholdResponse> {
    isUpdating.value = true;
    updateError.value = null;
    
    try {
      const response = await api.post<ThresholdResponse>('/settings/threshold', { threshold });
      await fetchSettings(); // Refresh settings
      return response;
    } catch (e) {
      updateError.value = e instanceof Error ? e.message : 'Failed to update threshold';
      throw e;
    } finally {
      isUpdating.value = false;
    }
  }

  return {
    settings,
    isUpdating,
    updateError,
    fetchSettings,
    updateThreshold,
  };
});
```

---

## 8. Views/Pages

### Dashboard View

```typescript
// src/views/DashboardView.vue
<script setup lang="ts">
import { onMounted, computed } from 'vue';
import { useStatsStore } from '@/stores/stats';
import { useThreatsStore } from '@/stores/threats';
import StatsCard from '@/components/dashboard/StatsCard.vue';
import ThreatChart from '@/components/dashboard/ThreatChart.vue';
import RecentThreats from '@/components/dashboard/RecentThreats.vue';
import SystemHealth from '@/components/dashboard/SystemHealth.vue';

const statsStore = useStatsStore();
const threatsStore = useThreatsStore();

onMounted(async () => {
  await Promise.all([
    statsStore.fetchStats(),
    threatsStore.fetchThreats(),
    threatsStore.fetchDistribution(),
  ]);
});

const stats = computed(() => statsStore.currentStats);
const distribution = computed(() => threatsStore.distribution);
</script>

<template>
  <div class="dashboard">
    <h1 class="text-2xl font-bold mb-6">Dashboard</h1>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <StatsCard
        title="Total Scans"
        :value="stats?.total || 0"
        icon="scan"
      />
      <StatsCard
        title="Critical Threats"
        :value="stats?.critical || 0"
        icon="danger"
        color="red"
      />
      <StatsCard
        title="High Threats"
        :value="stats?.high || 0"
        icon="warning"
        color="orange"
      />
      <StatsCard
        title="Bytes Scanned"
        :value="formatBytes(stats?.total_bytes_scanned || 0)"
        icon="data"
      />
    </div>
    
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <ThreatChart :data="distribution" />
      <SystemHealth />
    </div>
    
    <div class="mt-6">
      <RecentThreats :threats="threatsStore.threats.slice(0, 5)" />
    </div>
  </div>
</template>
```

### Scanner View

```typescript
// src/views/ScannerView.vue
<script setup lang="ts">
import { ref } from 'vue';
import { useScanStore } from '@/stores/scan';
import UrlScanner from '@/components/scanner/UrlScanner.vue';
import FileUploader from '@/components/scanner/FileUploader.vue';
import ScanResult from '@/components/scanner/ScanResult.vue';

const scanStore = useScanStore();
const activeTab = ref<'url' | 'file'>('url');

async function handleUrlScan(url: string, blockOnDetection: boolean) {
  await scanStore.scanUrl({ url, block_on_detection: blockOnDetection });
}

async function handleFileUpload(file: File, blockOnDetection: boolean) {
  await scanStore.scanFile(file, blockOnDetection);
}
</script>

<template>
  <div class="scanner">
    <h1 class="text-2xl font-bold mb-6">Malware Scanner</h1>
    
    <div class="tabs">
      <button 
        :class="{ active: activeTab === 'url' }"
        @click="activeTab = 'url'"
      >
        URL Scanner
      </button>
      <button 
        :class="{ active: activeTab === 'file' }"
        @click="activeTab = 'file'"
      >
        File Scanner
      </button>
    </div>
    
    <div class="tab-content">
      <UrlScanner 
        v-if="activeTab === 'url'"
        @scan="handleUrlScan"
        :is-scanning="scanStore.isScanning"
      />
      <FileUploader 
        v-if="activeTab === 'file'"
        @upload="handleFileUpload"
        :is-scanning="scanStore.isScanning"
      />
    </div>
    
    <div v-if="scanStore.currentScan" class="mt-6">
      <ScanResult :result="scanStore.currentScan" />
    </div>
  </div>
</template>
```

### Threats View

```typescript
// src/views/ThreatsView.vue
<script setup lang="ts">
import { onMounted } from 'vue';
import { useThreatsStore } from '@/stores/threats';
import ThreatTable from '@/components/threats/ThreatTable.vue';
import ThreatFilters from '@/components/threats/ThreatFilters.vue';
import ThreatStats from '@/components/threats/ThreatStats.vue';

const threatsStore = useThreatsStore();

onMounted(() => {
  threatsStore.fetchThreats();
  threatsStore.fetchStats();
});
</script>

<template>
  <div class="threats-view">
    <h1 class="text-2xl font-bold mb-6">Threat Logs</h1>
    
    <ThreatStats />
    
    <ThreatFilters 
      :filters="threatsStore.filters"
      @filter="threatsStore.updateFilters"
    />
    
    <ThreatTable
      :threats="threatsStore.threats"
      :loading="threatsStore.isLoading"
      :total="threatsStore.totalCount"
      :limit="threatsStore.filters.limit"
      :offset="threatsStore.filters.offset"
      @page-change="threatsStore.setPage"
    />
  </div>
</template>
```

### Settings View

```typescript
// src/views/SettingsView.vue
<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { useSettingsStore } from '@/stores/settings';
import ThresholdSlider from '@/components/settings/ThresholdSlider.vue';
import SettingsForm from '@/components/settings/SettingsForm.vue';

const settingsStore = useSettingsStore();
const newThreshold = ref(0.7);
const isUpdating = ref(false);
const updateMessage = ref('');

onMounted(() => {
  settingsStore.fetchSettings();
  if (settingsStore.settings) {
    newThreshold.value = settingsStore.settings.confidence_threshold;
  }
});

async function handleThresholdChange(value: number) {
  isUpdating.value = true;
  updateMessage.value = '';
  
  try {
    const response = await settingsStore.updateThreshold(value);
    updateMessage.value = `Threshold updated from ${response.old_threshold} to ${response.new_threshold}`;
  } catch {
    updateMessage.value = 'Failed to update threshold';
  } finally {
    isUpdating.value = false;
  }
}

const riskLevels = computed(() => settingsStore.settings?.risk_levels);
</script>

<template>
  <div class="settings-view">
    <h1 class="text-2xl font-bold mb-6">Settings</h1>
    
    <div class="grid gap-6">
      <section class="card">
        <h2 class="text-xl font-semibold mb-4">Detection Threshold</h2>
        <p class="text-gray-600 mb-4">
          Adjust the confidence threshold for malware detection.
          Higher values mean fewer false positives but more false negatives.
        </p>
        <ThresholdSlider
          v-model="newThreshold"
          :risk-levels="riskLevels"
          @update:model-value="handleThresholdChange"
          :disabled="isUpdating"
        />
        <p v-if="updateMessage" class="mt-2 text-sm" :class="{
          'text-green-600': updateMessage.includes('updated'),
          'text-red-600': updateMessage.includes('Failed')
        }">
          {{ updateMessage }}
        </p>
      </section>
      
      <section class="card">
        <h2 class="text-xl font-semibold mb-4">Current Configuration</h2>
        <SettingsForm :settings="settingsStore.settings" />
      </section>
    </div>
  </div>
</template>
```

---

## 9. Router Configuration

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Dashboard' },
  },
  {
    path: '/scanner',
    name: 'Scanner',
    component: () => import('@/views/ScannerView.vue'),
    meta: { title: 'Malware Scanner' },
  },
  {
    path: '/threats',
    name: 'Threats',
    component: () => import('@/views/ThreatsView.vue'),
    meta: { title: 'Threat Logs' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: 'Settings' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: 'Page Not Found' },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'Malware Detection'} | Real-Time Gateway`;
  next();
});

export default router;
```

---

## 10. Tailwind Configuration

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Risk level colors
        risk: {
          benign: '#22c55e',
          low: '#84cc16',
          medium: '#eab308',
          high: '#f97316',
          critical: '#ef4444',
        },
        // Brand colors
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
```

---

## 11. Environment Variables

```bash
# .env.example
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Malware Detection Gateway
VITE_APP_VERSION=1.0.0
```

---

## 12. Build & Deployment

### Vite Config

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          charts: ['chart.js', 'vue-chartjs'],
        },
      },
    },
  },
});
```

### TypeScript Config

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

---

## 13. UI/UX Requirements

### Risk Level Color Scheme

| Risk Level | Color | Hex Code | Meaning |
|------------|-------|----------|---------|
| BENIGN | Green | `#22c55e` | Safe, allow |
| LOW | Lime | `#84cc16` | Monitor, log only |
| MEDIUM | Yellow | `#eab308` | Warn, log |
| HIGH | Orange | `#f97316` | Alert, block |
| CRITICAL | Red | `#ef4444` | Block immediately |

### Loading States

- Use skeleton loaders for table rows
- Show progress bar during scans
- Disable buttons while scanning
- Show toast notifications for errors

### Responsive Design

- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Sidebar should collapse on mobile
- Tables should scroll horizontally on small screens

### Charts & Visualizations

- Threat distribution pie/doughnut chart
- Timeline chart for threats over time
- Bar chart for risk level counts
- Real-time update capability using polling

---

## 14. Error Handling

```typescript
// src/composables/useApi.ts
import { ref } from 'vue';
import type { ErrorResponse } from '@/types';

export function useApi() {
  const error = ref<ErrorResponse | null>(null);
  const isLoading = ref(false);

  async function apiCall<T>(
    request: () => Promise<T>
  ): Promise<T | null> {
    isLoading.value = true;
    error.value = null;
    
    try {
      return await request();
    } catch (e) {
      if (e && typeof e === 'object' && 'response' in e) {
        const axiosError = e as { response: { data: ErrorResponse } };
        error.value = axiosError.response.data;
      } else {
        error.value = {
          error: 'UNKNOWN_ERROR',
          message: e instanceof Error ? e.message : 'An unknown error occurred',
          timestamp: new Date().toISOString(),
        };
      }
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    error,
    isLoading,
    apiCall,
  };
}
```

---

## 15. Utility Functions

```typescript
// src/utils/formatters.ts
import { format, formatDistanceToNow } from 'date-fns';

export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function formatDate(date: string | Date): string {
  return format(new Date(date), 'yyyy-MM-dd HH:mm:ss');
}

export function formatRelativeTime(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function formatPercentage(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}min`;
}
```

```typescript
// src/utils/risk.ts
import type { RiskLevel } from '@/types';

export function getRiskColor(level: RiskLevel): string {
  const colors: Record<RiskLevel, string> = {
    [RiskLevel.BENIGN]: 'text-green-600 bg-green-100',
    [RiskLevel.LOW]: 'text-lime-600 bg-lime-100',
    [RiskLevel.MEDIUM]: 'text-yellow-600 bg-yellow-100',
    [RiskLevel.HIGH]: 'text-orange-600 bg-orange-100',
    [RiskLevel.CRITICAL]: 'text-red-600 bg-red-100',
  };
  return colors[level];
}

export function getRiskIcon(level: RiskLevel): string {
  const icons: Record<RiskLevel, string> = {
    [RiskLevel.BENIGN]: 'check-circle',
    [RiskLevel.LOW]: 'information',
    [RiskLevel.MEDIUM]: 'exclamation',
    [RiskLevel.HIGH]: 'exclamation-triangle',
    [RiskLevel.CRITICAL]: 'x-circle',
  };
  return icons[level];
}

export function getRiskValue(level: RiskLevel): number {
  const values: Record<RiskLevel, number> = {
    [RiskLevel.BENIGN]: 1,
    [RiskLevel.LOW]: 2,
    [RiskLevel.MEDIUM]: 3,
    [RiskLevel.HIGH]: 4,
    [RiskLevel.CRITICAL]: 5,
  };
  return values[level];
}
```

---

## 16. Testing Requirements

### Component Tests

```typescript
// tests/unit/ScanStore.spec.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useScanStore } from '@/stores/scan';

describe('ScanStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });
  
  it('should scan URL successfully', async () => {
    const store = useScanStore();
    // Test implementation
  });
  
  it('should handle scan errors', async () => {
    const store = useScanStore();
    // Test implementation
  });
});
```

### API Integration Tests

```typescript
// tests/e2e/scanner.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Scanner', () => {
  test('should scan URL and show result', async ({ page }) => {
    await page.goto('/scanner');
    await page.fill('input[placeholder="Enter URL to scan"]', 'http://example.com');
    await page.click('button:has-text("Scan")');
    await expect(page.locator('.scan-result')).toBeVisible();
  });
});
```

---

## 17. Project Structure Summary

```
frontend/
├── src/
│   ├── api/               # API client and endpoint functions
│   ├── assets/            # Static assets (images, styles)
│   ├── components/        # Reusable Vue components
│   │   ├── common/        # Generic UI components
│   │   ├── dashboard/     # Dashboard-specific components
│   │   ├── scanner/       # Scanner-related components
│   │   ├── threats/       # Threat management components
│   │   └── settings/      # Settings components
│   ├── composables/       # Vue composition functions
│   ├── config/            # Configuration files
│   ├── router/            # Vue Router setup
│   ├── stores/            # Pinia stores
│   ├── types/             # TypeScript type definitions
│   ├── utils/             # Utility functions
│   ├── views/             # Page components
│   ├── App.vue            # Root component
│   └── main.ts            # Application entry point
├── tests/                 # Test files
├── index.html             # HTML template
├── package.json           # Dependencies
├── tsconfig.json          # TypeScript config
├── vite.config.ts         # Vite config
├── tailwind.config.js     # Tailwind CSS config
└── .env                   # Environment variables
```

---

## 18. Development Workflow

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Run linting
npm run lint
```

### Code Style

- Use TypeScript strict mode
- Follow Vue 3 Composition API style guide
- Use `<script setup>` syntax for components
- Keep components small and focused
- Use proper prop typing with TypeScript

---

This specification provides everything needed for another agent to implement the Vue + Vite + TypeScript frontend for the Real-Time Malware Detection Gateway.