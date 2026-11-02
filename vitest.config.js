import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    // Facet top-up tests render up to ~125 movies through jsdom; that runs
    // well under the 5s default locally but timed out on the shared CI
    // runner (Scrape and Update run 41384251805 annotations). 20s leaves
    // headroom while still catching real hangs.
    testTimeout: 20000,
  },
});
