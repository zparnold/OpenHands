# Frontend Development Guide (frontend/)

This guide provides detailed information for developing the OpenHands React frontend.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Directories](#key-directories)
3. [Development Workflow](#development-workflow)
4. [Testing Guidelines](#testing-guidelines)
5. [Common Patterns](#common-patterns)
6. [Common Tasks](#common-tasks)

---

## Architecture Overview

The OpenHands frontend is a React single-page application built with:
- **React 18+**: Component framework
- **TypeScript**: Type safety
- **TanStack Query (React Query)**: Data fetching and caching
- **React Router**: Client-side routing
- **Tailwind CSS**: Styling
- **Vite**: Build tool
- **Vitest**: Testing framework

**Architecture layers:**
```
┌─────────────────────────────────────┐
│   Routes (routes/)                  │ ← Page components
├─────────────────────────────────────┤
│   Components (components/)          │ ← Reusable UI components
├─────────────────────────────────────┤
│   TanStack Query Hooks (hooks/)     │ ← Data fetching layer
├─────────────────────────────────────┤
│   API Client (api/)                 │ ← HTTP client (Data Access Layer)
├─────────────────────────────────────┤
│   Backend API (FastAPI)             │ ← REST/WebSocket endpoints
└─────────────────────────────────────┘
```

**Critical architectural rule:**
```
UI Components → TanStack Query Hooks → API Client → Backend API
```

**Never** call API client methods directly from components!

---

## Key Directories

### src/
Root source directory.

**Main subdirectories:**

### src/api/
API client methods (Data Access Layer).

**Key files:**
- `github.ts`: GitHub integration
- `open-hands.ts`: Core OpenHands API
- `options.ts`: Configuration options
- `axios-instance.ts`: Configured axios client

**⚠️ IMPORTANT**: Never call these methods directly from components. Always wrap them in TanStack Query hooks.

### src/hooks/
Custom React hooks.

**Subdirectories:**
- `query/`: TanStack Query hooks for data fetching (use[Resource] pattern)
  - Example: `useConversationSkills`, `useSettings`, `useMessages`
- `mutation/`: TanStack Query mutation hooks (use[Action] pattern)
  - Example: `useDeleteConversation`, `useSaveSettings`, `useSendMessage`
- Other custom hooks for non-data-fetching logic

**Pattern:**
- Query hooks: `use[Resource]` (e.g., `useUser`)
- Mutation hooks: `use[Action]` (e.g., `useUpdateUser`)

### src/components/
Reusable React components.

**Organization:**
- Small, focused components
- Props defined with TypeScript interfaces
- Use composition over inheritance
- Export from index.ts files

### src/routes/
Page-level components.

**Examples:**
- `app-settings.tsx`: Settings page
- `conversation.tsx`: Chat interface
- `login.tsx`: Login page

### src/types/
TypeScript type definitions.

**Key files:**
- `action-type.ts`: Agent action types
- `settings.ts`: Settings types
- `message.ts`: Message types

### src/i18n/
Internationalization.

**Key files:**
- `translation.json`: Translation strings
- `declaration.ts`: TypeScript declarations for i18n
- `index.ts`: i18n configuration

**Adding translations:**
1. Add key/value to `translation.json`
2. Run `npm run make-i18n` to update `declaration.ts`
3. Use in components: `const { t } = useTranslation();`

### src/context/
React Context providers.

**Examples:**
- Settings context
- Auth context
- Theme context

### src/utils/
Utility functions.

**Examples:**
- `verified-models.ts`: LLM model lists
- `utils.ts`: Helper functions

---

## Development Workflow

### Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start dev server:**
```bash
npm run dev
```

3. **Open browser:**
Navigate to `http://localhost:3001` (or configured port)

### Making Changes

1. **Create/modify components** in `src/components/` or `src/routes/`
2. **Add/update TanStack Query hooks** in `src/hooks/query/` or `src/hooks/mutation/`
3. **Update types** in `src/types/` if needed
4. **Add tests** in `__tests__/` or `tests/`
5. **Run linting:**
```bash
npm run lint:fix
```
6. **Run tests:**
```bash
npm run test
```
7. **Build:**
```bash
npm run build
```

### Development Commands

```bash
# Development server with hot reload
npm run dev

# Type checking
npm run typecheck

# Linting
npm run lint          # Check only
npm run lint:fix      # Fix automatically

# Testing
npm run test          # Run all tests
npm run test -- -t "TestName"  # Run specific test
npm run test -- --watch        # Watch mode

# Building
npm run build         # Production build

# i18n
npm run make-i18n     # Update i18n declarations
```

---

## Testing Guidelines

### Test Structure

Tests use **Vitest** and **React Testing Library**.

**Test locations:**
- `__tests__/`: Component tests
- `tests/`: Integration tests
- Co-located: Tests next to source files

### Writing Tests

**Component test example:**
```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MyComponent } from './my-component';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('handles click events', async () => {
    const { user } = render(<MyComponent />);
    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Clicked')).toBeInTheDocument();
  });
});
```

**TanStack Query hook test:**
```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { useMyData } from './use-my-data';

describe('useMyData', () => {
  it('fetches data successfully', async () => {
    const queryClient = new QueryClient();
    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useMyData(), { wrapper });
    
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
  });
});
```

**Mocking API calls:**
Use MSW (Mock Service Worker) for API mocking:

```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/data', (req, res, ctx) => {
    return res(ctx.json({ data: 'mocked' }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Running Tests

```bash
# Run all tests
npm run test

# Run specific test file
npm run test src/components/my-component.test.tsx

# Run tests matching pattern
npm run test -- -t "renders correctly"

# Watch mode
npm run test -- --watch

# Coverage report
npm run test -- --coverage
```

---

## Common Patterns

### Data Fetching with TanStack Query

**Query hook (GET request):**
```typescript
// src/hooks/query/use-my-data.ts
import { useQuery } from '@tanstack/react-query';
import { getMyData } from '#/api/my-api';

export const useMyData = () => {
  return useQuery({
    queryKey: ['myData'],
    queryFn: getMyData,
  });
};
```

**Usage in component:**
```typescript
import { useMyData } from '#/hooks/query/use-my-data';

export function MyComponent() {
  const { data, isLoading, error } = useMyData();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <div>{data.value}</div>;
}
```

**Mutation hook (POST/PUT/DELETE request):**
```typescript
// src/hooks/mutation/use-update-data.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateData } from '#/api/my-api';

export const useUpdateData = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateData,
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['myData'] });
    },
  });
};
```

**Usage in component:**
```typescript
import { useUpdateData } from '#/hooks/mutation/use-update-data';

export function MyComponent() {
  const updateMutation = useUpdateData();

  const handleUpdate = () => {
    updateMutation.mutate({ id: 1, value: 'new' });
  };

  return (
    <button onClick={handleUpdate} disabled={updateMutation.isPending}>
      {updateMutation.isPending ? 'Updating...' : 'Update'}
    </button>
  );
}
```

### Settings Patterns

There are **two patterns** for saving settings:

**Pattern 1: Entity-based Resources (Immediate Save)**
- Used for: API Keys, Secrets, MCP Servers
- Behavior: Changes saved immediately on action
- Implementation:
  - No "Save Changes" button
  - No local state or `isDirty` tracking
  - Dedicated mutation hooks for each operation
  - Example: `use-add-mcp-server.ts`, `use-delete-mcp-server.ts`

**Pattern 2: Form-based Settings (Manual Save)**
- Used for: Application settings, LLM configuration
- Behavior: Changes accumulated locally and saved on button click
- Implementation:
  - Has "Save Changes" button (enabled when dirty)
  - Local state with `isDirty` tracking
  - Uses `useSaveSettings` hook
  - Example: LLM tab, Application tab

**When to use:**
- Use Pattern 1 for entity management (independent items)
- Use Pattern 2 for configuration forms (interdependent settings)

### Component Composition

**Small, focused components:**
```typescript
// Bad: One large component
function Dashboard() {
  return (
    <div>
      <header>...</header>
      <sidebar>...</sidebar>
      <main>...</main>
      <footer>...</footer>
    </div>
  );
}

// Good: Composed from smaller components
function Dashboard() {
  return (
    <div>
      <DashboardHeader />
      <DashboardSidebar />
      <DashboardMain />
      <DashboardFooter />
    </div>
  );
}
```

### Type Safety

**Always define prop types:**
```typescript
interface MyComponentProps {
  title: string;
  count?: number;
  onUpdate: (value: string) => void;
}

export function MyComponent({ title, count = 0, onUpdate }: MyComponentProps) {
  // ...
}
```

**Use discriminated unions for variants:**
```typescript
type ButtonVariant = 
  | { variant: 'primary'; color: string }
  | { variant: 'secondary' }
  | { variant: 'danger'; confirmText: string };

function Button(props: ButtonVariant) {
  switch (props.variant) {
    case 'primary':
      return <PrimaryButton color={props.color} />;
    case 'secondary':
      return <SecondaryButton />;
    case 'danger':
      return <DangerButton confirmText={props.confirmText} />;
  }
}
```

---

## Common Tasks

### Adding a New Page

1. **Create route component** in `src/routes/`:
```typescript
// src/routes/my-new-page.tsx
export function MyNewPage() {
  return <div>My New Page</div>;
}
```

2. **Add route** in `src/routes.ts`:
```typescript
export const routes = [
  // ... existing routes
  {
    path: '/my-new-page',
    component: lazy(() => import('./routes/my-new-page')),
  },
];
```

3. **Add navigation link** if needed

### Adding a New API Endpoint

1. **Add API method** in `src/api/`:
```typescript
// src/api/my-api.ts
import { axiosInstance } from './axios-instance';

export async function getMyData(): Promise<MyData> {
  const { data } = await axiosInstance.get('/api/my-data');
  return data;
}
```

2. **Create TanStack Query hook** in `src/hooks/query/`:
```typescript
// src/hooks/query/use-my-data.ts
import { useQuery } from '@tanstack/react-query';
import { getMyData } from '#/api/my-api';

export const useMyData = () => {
  return useQuery({
    queryKey: ['myData'],
    queryFn: getMyData,
  });
};
```

3. **Use in component:**
```typescript
import { useMyData } from '#/hooks/query/use-my-data';

export function MyComponent() {
  const { data } = useMyData();
  // ...
}
```

### Adding a New Action Type

1. **Add to `action-type.ts`:**
```typescript
export const ActionType = {
  // ... existing types
  MY_NEW_ACTION: 'my_new_action',
} as const;
```

2. **Add to `HANDLED_ACTIONS`** in `src/state/chat-slice.ts` if it should be collapsible:
```typescript
const HANDLED_ACTIONS = [
  // ... existing actions
  ActionType.MY_NEW_ACTION,
];
```

3. **Implement action handling** in `addAssistantAction` function

4. **Add translation key** in `src/i18n/translation.json`:
```json
{
  "ACTION_MESSAGE$MY_NEW_ACTION": "My new action message"
}
```

5. **Run `npm run make-i18n`** to update declarations

### Adding a User Setting

See the "Adding User Settings" section in the root AGENTS.md for detailed instructions on adding settings to both frontend and backend.

### Adding a New LLM Model

1. **Add to `verified-models.ts`:**
```typescript
export const VERIFIED_MODELS = [
  // ... existing models
  'new-model-name',
];

// Add to provider-specific array
export const VERIFIED_OPENAI_MODELS = [
  // ... existing models
  'new-model-name',
];
```

2. **Follow backend steps** in root AGENTS.md

3. **Test model selection** in UI

---

## Best Practices

1. **Always use TanStack Query hooks** - Never call API methods directly from components
2. **Type everything** - Define interfaces for all props and data structures
3. **Keep components small** - Single responsibility principle
4. **Use composition** - Combine small components into larger ones
5. **Test user interactions** - Not implementation details
6. **Accessibility** - Use semantic HTML and ARIA labels
7. **Responsive design** - Use Tailwind's responsive utilities
8. **Error handling** - Always handle loading and error states
9. **Memoization** - Use `useMemo` and `useCallback` for expensive operations
10. **Code splitting** - Lazy load routes and heavy components

---

## Troubleshooting

### Build errors
- Check TypeScript errors: `npm run typecheck`
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check for duplicate dependencies

### Linting errors
- Run `npm run lint:fix` to auto-fix
- Check for unused imports
- Verify import paths

### Tests failing
- Check for missing test setup
- Verify mocks are correct
- Ensure async operations are awaited
- Check for race conditions

### State not updating
- Verify TanStack Query is invalidating cache
- Check mutation `onSuccess` callbacks
- Ensure query keys are correct

### Type errors
- Run `npm run typecheck` to see all errors
- Check import paths
- Verify API types match backend

---

## Environment Variables

Set in `frontend/.env` or as environment variables:

- `VITE_BACKEND_HOST`: Backend API host (default: `127.0.0.1`)
- `VITE_BACKEND_PORT`: Backend API port (default: `3000`)
- `VITE_USE_TLS`: Use HTTPS for API calls (default: `false`)
- `VITE_INSECURE_SKIP_VERIFY`: Skip TLS verification (default: `false`)
- `VITE_FRONTEND_PORT`: Frontend dev server port (default: `3001`)

---

## Integration Points

### With Backend
- REST API via `axios` in `src/api/`
- WebSocket for real-time updates
- TanStack Query for caching and state management

### With TanStack Query
- Query hooks for GET requests
- Mutation hooks for POST/PUT/DELETE requests
- Cache invalidation on mutations
- Optimistic updates where appropriate

### With Tailwind CSS
- Utility-first styling
- Responsive design with breakpoints
- Custom theme in `tailwind.config.js`

---

For backend API documentation, see [../openhands/server/AGENTS.md](../openhands/server/AGENTS.md).
For general development guidelines, see [../AGENTS.md](../AGENTS.md).
