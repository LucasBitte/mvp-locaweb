import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' }
})

export async function fetchAPI(endpoint: string, params?: Record<string, any>) {
  try {
    const res = await client.get(endpoint, { params })
    return res.data
  } catch (err) {
    console.error(`Erro em ${endpoint}:`, err)
    throw err
  }
}
