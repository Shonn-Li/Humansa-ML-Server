# Dark Mode Toggle - Requirements Specification

## Problem Statement
Users need the ability to toggle between light and dark themes in the application settings, with their preference persisted across sessions and applied consistently across all platforms (iOS, Android, Web).

## Solution Overview
Implement a comprehensive dark mode system with a toggle in settings, centralized theme management via Redux, and a ThemeProvider component for consistent theme application across all components.

## Functional Requirements

### FR1: Theme Toggle Interface
- **Requirement**: Visual toggle switch in settings page
- **Location**: `app/(tabs)/settings.tsx`
- **Behavior**: Switch between light/dark modes instantly
- **Accessibility**: Proper labeling and keyboard navigation support

### FR2: Theme Persistence
- **Requirement**: User theme preference must persist across app sessions
- **Implementation**: Redux store with persistence (AsyncStorage)
- **Default**: Light mode for new users

### FR3: Multi-Platform Support
- **Requirement**: Dark mode must work on iOS, Android, and Web
- **Implementation**: Single theme system with platform-aware styling where needed
- **Consistency**: Identical visual appearance across platforms

### FR4: Global Theme Application
- **Requirement**: All app components must respect the selected theme
- **Coverage**: Navigation, buttons, text, backgrounds, borders, icons
- **Performance**: Theme changes should be instant without flickering

### FR5: Accessibility Compliance
- **Requirement**: Dark mode must meet accessibility standards
- **Contrast**: Minimum 4.5:1 contrast ratio for normal text
- **Support**: Screen reader announcements for theme changes

## Technical Requirements

### TR1: Redux Integration
- **File**: `store/themeSlice.ts` (new)
- **Pattern**: Redux Toolkit slice following existing store patterns
- **State**: `{ theme: 'light' | 'dark', systemPreference: boolean }`
- **Actions**: `setTheme`, `toggleTheme`, `setSystemPreference`

### TR2: Theme Configuration
- **File**: `config/themes.ts` (new)
- **Structure**: Centralized color definitions for light and dark themes
- **Format**: 
  ```typescript
  {
    light: { background: '#ffffff', text: '#000000', ... },
    dark: { background: '#121212', text: '#ffffff', ... }
  }
  ```

### TR3: Theme Provider Component
- **File**: `components/Common/ThemeProvider.tsx` (new)
- **Purpose**: Wrap app to provide theme context
- **Integration**: Connect to Redux store and provide theme values
- **Location**: Wrap in `app/_layout.tsx`

### TR4: Settings Integration
- **File**: `app/(tabs)/settings.tsx` (modify)
- **Component**: Add theme toggle switch component
- **Position**: Logical grouping with other user preferences
- **Styling**: Consistent with existing settings items

### TR5: Component Updates
- **Scope**: All existing components in `components/` directory
- **Pattern**: Use theme values instead of hardcoded colors
- **Migration**: Gradual update of components to use theme system
- **Testing**: Verify all components work in both themes

## Implementation Patterns

### Theme Usage Pattern
```typescript
// In components
const theme = useTheme(); // from ThemeProvider
const styles = StyleSheet.create({
  container: {
    backgroundColor: theme.background,
    color: theme.text
  }
});
```

### Redux Integration Pattern
```typescript
// In components that need theme control
const dispatch = useDispatch();
const currentTheme = useSelector(state => state.theme.current);
const toggleTheme = () => dispatch(themeActions.toggleTheme());
```

### Settings Toggle Pattern
```typescript
// In settings page
<SettingsItem 
  title="Dark Mode"
  control={<Switch value={isDark} onValueChange={handleToggle} />}
/>
```

## File Changes Required

### New Files
1. `store/themeSlice.ts` - Redux slice for theme management
2. `config/themes.ts` - Theme color definitions
3. `components/Common/ThemeProvider.tsx` - Theme context provider
4. `components/Common/ThemeSwitch.tsx` - Reusable toggle component

### Modified Files
1. `app/_layout.tsx` - Add ThemeProvider wrapper
2. `app/(tabs)/settings.tsx` - Add theme toggle to settings
3. `store/index.ts` - Register theme slice
4. All components in `components/` - Update to use theme colors

## Acceptance Criteria

### AC1: Toggle Functionality
- [ ] Toggle switch appears in settings page
- [ ] Clicking toggle immediately changes app theme
- [ ] Toggle state reflects current theme accurately
- [ ] Toggle is accessible via screen readers

### AC2: Theme Persistence
- [ ] Theme preference saves automatically when changed
- [ ] App opens with previously selected theme
- [ ] Theme persists across app updates
- [ ] Default theme is light for new installations

### AC3: Visual Consistency
- [ ] All text is readable in both themes
- [ ] All components respect the selected theme
- [ ] No hardcoded colors remain in components
- [ ] Theme changes apply instantly without restart

### AC4: Platform Support
- [ ] Dark mode works identically on iOS
- [ ] Dark mode works identically on Android  
- [ ] Dark mode works identically on Web
- [ ] No platform-specific visual bugs

### AC5: Performance
- [ ] Theme switching is instant (<100ms)
- [ ] No flickering during theme changes
- [ ] App startup time unchanged
- [ ] Memory usage remains stable

### AC6: Testing Requirements
- [ ] Unit tests for theme slice actions
- [ ] Component tests with both themes
- [ ] Integration tests for settings toggle
- [ ] E2E tests for theme persistence
- [ ] Accessibility tests for contrast and navigation

## Dependencies
- No new external dependencies required
- Uses existing Redux Toolkit and AsyncStorage
- Leverages existing component patterns

## Rollback Plan
- Theme slice can be disabled via feature flag
- Default to light theme if theme system fails
- Existing hardcoded colors remain as fallback

---

**Ready for Implementation**: This specification provides complete requirements for implementing dark mode toggle functionality.