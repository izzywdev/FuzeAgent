/// <reference types="@testing-library/jest-dom" />

import '@testing-library/jest-dom/matchers'

declare global {
  namespace Vi {
    interface JestAssertion<T = any>
      extends jest.Matchers<void, T>,
        Record<string, any> {}
  }
}