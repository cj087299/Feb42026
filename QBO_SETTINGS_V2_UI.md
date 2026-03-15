# QuickBooks Settings v2 - UI Preview

## Page Layout

### Header Section
- **Title**: "⚙️ QuickBooks Settings" with a purple "v2" badge
- **Navigation Links**: Home | Invoices | Cash Flow | Logout button
- **Styling**: White background with rounded corners, purple gradient page background

### Main Content Section

#### Title and Description
- **Heading**: "QuickBooks Online Connection"
- **Description**: "Connect your QuickBooks Online account to sync invoices, manage cash flow, and access financial data."

#### Connection Status Box
A light gray box displaying:
- **Connection Status**: Red badge showing "Not Connected"
- **Message**: "Click the button below to connect to QuickBooks Online"

When connected, it will show:
- Connection Status: Green badge showing "Connected"
- Company ID: [Company ID from QBO]
- Last Connected: [Timestamp]

#### Connect Button
- **Large green button** with:
  - 📊 icon on the left
  - "Connect to QuickBooks" text
  - Hover effect: Slightly darker green with elevation
  - Loading state: Shows spinner and "Connecting..." text

#### Information Note
A blue info box at the bottom with:
- **Icon**: ℹ️ How It Works
- **Text**: Explains the OAuth flow process
- Tells users they'll be redirected to QuickBooks to log in
- Notes that tokens will be securely stored after authorization

## Color Scheme
- **Page Background**: Purple gradient (#667eea to #764ba2)
- **Card Background**: White
- **Primary Action Button**: Green (#2ca01c)
- **Status Badge - Connected**: Light green background, dark green text
- **Status Badge - Not Connected**: Light red background, dark red text
- **Info Note**: Light blue background with blue left border
- **Version Badge**: Purple background, white text

## User Experience Flow
1. User navigates to /qbo-settings-v2
2. Page loads showing "Not Connected" status
3. User clicks the green "Connect to QuickBooks" button
4. Button changes to show loading spinner
5. Popup window opens with QuickBooks login
6. User logs into QuickBooks and authorizes
7. Popup closes automatically
8. Success message appears
9. Status updates to show "Connected" with company details

## Responsive Design
- Maximum width: 800px centered
- Padding on mobile devices
- Button remains prominent on all screen sizes

## Key Improvements Over v1
1. **Cleaner Interface**: Single button instead of multiple form fields
2. **Clear Status**: Connection status prominently displayed
3. **Better Feedback**: Loading states and success messages
4. **Modern Design**: Matches existing app styling with gradient and shadows
5. **No Form Validation Needed**: Eliminates redirect loop issues
