export const TOKEN_KEY = 'auth_token'
export const LOCATION_KEY = 'user_location'
export const CATEGORY_KEY = 'user_category'
export const STORE_NAME_KEY = 'user_store_name'

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

export const ADM_CD_KEY = 'user_adm_cd'
export const DONG_NAME_KEY = 'user_dong_name'

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
