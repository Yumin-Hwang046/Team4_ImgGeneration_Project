export const TOKEN_KEY = 'auth_token'
export const LOCATION_KEY = 'user_location'
export const CATEGORY_KEY = 'user_category'
export const STORE_NAME_KEY = 'user_store_name'
export const MOOD_KEY = 'user_mood'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getStoredLocation(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(LOCATION_KEY) ?? ''
}

export function setStoredLocation(location: string): void {
  localStorage.setItem(LOCATION_KEY, location)
}

export function getStoredCategory(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(CATEGORY_KEY) ?? ''
}

export function setStoredCategory(category: string): void {
  localStorage.setItem(CATEGORY_KEY, category)
}

export function getStoredStoreName(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(STORE_NAME_KEY) ?? ''
}

export function setStoredStoreName(name: string): void {
  localStorage.setItem(STORE_NAME_KEY, name)
}

export function getStoredMood(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(MOOD_KEY) ?? ''
}

export function setStoredMood(mood: string): void {
  localStorage.setItem(MOOD_KEY, mood)
}

export const ADM_CD_KEY = 'user_adm_cd'
export const DONG_NAME_KEY = 'user_dong_name'
export const LAT_KEY = 'user_lat'
export const LNG_KEY = 'user_lng'

export function getStoredAdmCd(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(ADM_CD_KEY) ?? ''
}

export function setStoredAdmCd(admCd: string): void {
  localStorage.setItem(ADM_CD_KEY, admCd)
}

export function getStoredDongName(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(DONG_NAME_KEY) ?? ''
}

export function setStoredDongName(dong: string): void {
  localStorage.setItem(DONG_NAME_KEY, dong)
}

export function getStoredLat(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(LAT_KEY) ?? ''
}

export function setStoredLat(lat: string): void {
  localStorage.setItem(LAT_KEY, lat)
}

export function getStoredLng(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(LNG_KEY) ?? ''
}

export function setStoredLng(lng: string): void {
  localStorage.setItem(LNG_KEY, lng)
}

export const MOOD_KEY = 'stored_mood'

export function getStoredMood(): string {
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(MOOD_KEY) ?? ''
}

export function setStoredMood(mood: string): void {
  localStorage.setItem(MOOD_KEY, mood)
}
