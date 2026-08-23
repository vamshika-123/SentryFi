/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // --- Light fintech palette ---
        background:   '#F8FAFC', // near-white, slightly cool
        surface:      '#FFFFFF', // card backgrounds
        'surface-alt':'#F1F5F9', // secondary panels / alternating rows
        border:       '#E2E8F0', // default border colour

        // Brand
        primary:      '#1E40AF', // confident navy/deep blue
        'primary-hover': '#1D3EA0',

        // Text
        'text-primary':   '#0F172A', // near-black
        'text-secondary': '#64748B', // medium-grey

        // Semantic
        success:  '#16A34A', // clean/safe green
        danger:   '#DC2626', // flagged/fraud red
        warning:  '#D97706', // needs-review amber

        // Risk badges (aliased to semantics)
        'risk-low':    '#16A34A',
        'risk-medium': '#D97706',
        'risk-high':   '#DC2626',
      },
    },
  },
  plugins: [],
}
