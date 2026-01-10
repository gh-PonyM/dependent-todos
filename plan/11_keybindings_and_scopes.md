# Keybindings in Different Layers

In Textual, keybindings can be defined at multiple levels in the application hierarchy: the App, individual Screens, and Widgets. Understanding how these layers interact is crucial for implementing correct keybinding behavior, especially for modals and focused components.

## Binding Hierarchy and Merging

1. **App-level Bindings**: Defined in the `BINDINGS` class attribute of your main `App` class. These are global and available throughout the application.

2. **Screen-level Bindings**: Defined in the `BINDINGS` class attribute of `Screen` subclasses. These are active only when that specific screen is the current screen (e.g., when a modal is open).

3. **Widget-level Bindings**: Defined in the `BINDINGS` class attribute of `Widget` subclasses. These are active when the widget has focus.

Textual merges bindings from all levels, with more specific bindings (closer to the focused widget) taking precedence over more general ones. If a key is bound at multiple levels, the most specific binding wins.

## Implementation for Modals and Screens

When opening a modal or switching screens:

- The new screen's bindings become active and "capture" key events
- App-level bindings are still available unless overridden by screen bindings
- Background screens do not receive key events while a modal is open

To implement this correctly:

- Define modal-specific keybindings on the modal screen class
- Use screen-level bindings for navigation within that screen
- Reserve app-level bindings for global actions (like quitting the app)
- For focused widgets (like inputs), define widget-specific bindings if needed

## Example Implementation

```python
class MyApp(App):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit app"),
        ("ctrl+n", "new_item", "New item"),
    ]

class ModalScreen(Screen):
    BINDINGS = [
        ("escape", "close_modal", "Close modal"),
        ("enter", "confirm", "Confirm action"),
    ]

class InputWidget(Widget):
    BINDINGS = [
        ("tab", "next_field", "Next field"),
        ("shift+tab", "prev_field", "Previous field"),
    ]
```

This layered approach ensures that keybindings are contextually appropriate and don't interfere with each other.

# Improvements TODO

- [x] On opening a screen, the keybindings must be captured there and not be passed to the background app
- [x] When clicking outside the modal, it should also close
- [x] I should be able to go forward and background with tab and shift+tab in the input fields of the model screen. Implement it in a ways that uses a query for current inputs used.
- [x] Adapt other modals to use the BaseModal to tidy up the code