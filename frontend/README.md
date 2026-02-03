# Contact Form UI

A responsive, user-friendly contact form with built-in validation.

## Features

- **Required Fields**: Name, email, and message fields
- **Email Validation**: Proper email format validation using regex
- **Real-time Validation**: Validates on blur and shows errors immediately
- **Character Counter**: Message field includes a character counter (max 1000 characters)
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **User-friendly UI**:
  - Clear error messages
  - Visual feedback on focus
  - Smooth animations
  - Success confirmation message
- **Accessibility**:
  - Proper labels and ARIA attributes
  - Keyboard navigation support
  - Autocomplete attributes for better UX

## Usage

### Opening the Form

Simply open the `contact-form.html` file in any modern web browser:

```bash
# From the project root
open frontend/contact-form.html

# Or on Linux
xdg-open frontend/contact-form.html

# Or on Windows
start frontend/contact-form.html
```

### Form Validation Rules

1. **Name**:
   - Required field
   - Minimum 2 characters

2. **Email**:
   - Required field
   - Must be a valid email format (example@domain.com)

3. **Message**:
   - Required field
   - Minimum 10 characters
   - Maximum 1000 characters

### Integration with Backend

The form currently simulates submission. To integrate with a backend API:

1. Replace the `setTimeout` block in the form submission handler with an actual API call:

```javascript
// Replace this section in the script:
fetch('/api/contact', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        name: nameInput.value.trim(),
        email: emailInput.value.trim(),
        message: messageInput.value.trim()
    })
})
.then(response => response.json())
.then(data => {
    // Show success message
    form.style.display = 'none';
    successMessage.classList.add('show');
    form.reset();
})
.catch(error => {
    console.error('Error:', error);
    alert('Failed to send message. Please try again.');
})
.finally(() => {
    submitButton.disabled = false;
    submitButton.textContent = 'Send Message';
});
```

## File Structure

```
frontend/
├── contact-form.html    # Main contact form (HTML + CSS + JavaScript)
└── README.md           # This documentation
```

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Customization

### Colors

The form uses a gradient color scheme. To customize:

```css
/* Background gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Button gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Size

Maximum form width can be adjusted:

```css
.container {
    max-width: 500px; /* Change this value */
}
```

### Validation Rules

Modify validation functions in the JavaScript section:

```javascript
function validateName() {
    // Customize validation logic here
}
```

## Testing

Test the form with various inputs:

1. **Valid submission**: Fill all fields correctly
2. **Empty fields**: Try submitting without filling fields
3. **Invalid email**: Use formats like "test" or "test@"
4. **Short message**: Enter less than 10 characters
5. **Mobile view**: Resize browser to test responsiveness

## License

This component is part of the MAO project.
