import '@testing-library/jest-dom'

class LocalStorageMock implements Storage {
  private store: Record<string, string> = {};

  get length(): number {
    return Object.keys(this.store).length;
  }

  clear(): void {
    this.store = {};
  }

  getItem(key: string): string | null {
    return this.store[key] || null;
  }

  key(index: number): string | null {
    return Object.keys(this.store)[index] || null;
  }

  removeItem(key: string): void {
    delete this.store[key];
  }

  setItem(key: string, value: string): void {
    this.store[key] = String(value);
  }
}

if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'localStorage', {
    value: new LocalStorageMock(),
    writable: true
  });
}

if (typeof global !== 'undefined') {
  Object.defineProperty(global, 'localStorage', {
    value: new LocalStorageMock(),
    writable: true
  });
}
