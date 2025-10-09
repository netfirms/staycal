### Guiding Principles

*   **Solve the Core Problem First:** The primary focus is to be the simplest, most reliable calendar and booking tool for small property owners.
*   **Fast Time-to-Value:** A new user should be able to sign up, create a property, add a room, and log their first booking in under 5 minutes.
*   **Monetization-Driven:** Features that encourage upgrades from the Free tier to a paid plan are prioritized.

---

### The Roadmap: Now, Next, Later

Here is a phased approach to the development and growth of GoStayPro.

### **Phase 1: Now (Next 1-3 Months) — Launch Readiness & Core Monetization**

The goal of this phase is to transition from an MVP to a commercially viable product. The focus is on implementing the billing system and solidifying the core user experience.

*   **Implement Self-Serve Billing with Stripe:**
    *   **Stripe Checkout Integration:** Allow users to securely subscribe to the Basic or Pro plans using Stripe Checkout.
    *   **Stripe Customer Portal:** Integrate the Stripe Customer Portal so users can manage their subscription, update payment methods, and cancel their plan without manual intervention.
    *   **Subscription Status Sync:** Use Stripe webhooks to automatically update a user's plan status (`active`, `cancelled`, `expired`) in the application database.

*   **Enforce Plan Limits:**
    *   Programmatically enforce the limits defined in the monetization strategy (e.g., block a Free user from creating a third room and prompt them with an upgrade CTA).
    *   Build middleware to check feature access based on the user's current subscription plan.

*   **Refine User Onboarding:**
    *   Improve the initial onboarding stepper to be more interactive and guided.
    *   Add in-app hints and tooltips for first-time users to explain key concepts like creating a booking directly from the calendar.

*   **Basic Reporting & Data Export:**
    *   Implement a simple CSV export for bookings within a selected date range. This is a low-effort, high-value feature for owners who need to do their own accounting.

### **Phase 2: Next (3-6 Months) — Driving Growth & Retention**

With the core product and billing in place, the focus shifts to features that make the application "sticky" and solve the user's next biggest problem: managing availability across multiple channels.

*   **Two-Way iCal Sync:**
    *   This is the highest-priority feature for this phase. Provide a unique iCal URL for each room that can be imported into external calendars like Airbnb, Booking.com, and Google Calendar.
    *   Allow users to import external iCal feeds into GoStayPro to block off availability, preventing double bookings. This is a major driver for upgrading to a Pro plan.

*   **Enhanced Calendar & Booking Management:**
    *   **Drag-and-Drop Editing:** Allow users to move and extend bookings directly on the FullCalendar interface.
    *   **Housekeeping View:** Create a simple daily or weekly view for staff to see which rooms need cleaning based on check-outs and check-ins.
    *   **Maintenance Blocks:** Allow owners to block off rooms for maintenance, making them unavailable for booking.

*   **Automated Notifications:**
    *   Implement email notifications for critical events:
        *   Confirmation email to the guest when a booking is created.
        *   Reminder email to the owner for upcoming check-ins/check-outs.
        *   Notification to the owner for new bookings.

*   **Advanced Overview & Analytics:**
    *   Enhance the Overview page with key metrics like Occupancy Rate, Average Daily Rate (ADR), and Revenue Per Available Room (RevPAR).
    *   Add more visual charts and graphs to track performance over time.

### **Phase 3: Later (6-12+ Months) — Strategic Expansion & Ecosystem**

This phase focuses on expanding the product's capabilities to serve larger clients and capture more value, turning GoStayPro from a simple tool into a platform.

*   **Direct Booking Engine:**
    *   Provide a simple, embeddable widget or a public-facing page that allows guests to see availability and book directly with the property. This helps owners save on high commission fees from OTAs (Online Travel Agencies). This would be a premium, Pro-tier feature.

*   **Advanced Pricing & Rate Management:**
    *   Build a rate manager that allows owners to set seasonal pricing, weekend/weekday rates, and rules for length-of-stay discounts.
    *   Visualize rates on a calendar to make it easy to manage.

*   **Guest CRM (Customer Relationship Management):**
    *   Create a central guest database to track stay history, contact information, and preferences.
    *   Allow owners to add notes and tags to guest profiles, enabling better customer service and targeted marketing.

*   **Public API & Third-Party Integrations:**
    *   Develop a secure, tenant-aware public API for Pro users.
    *   Explore integrations with accounting software (like Xero or QuickBooks) and other hospitality tools.

*   **Multi-Property Portfolio View:**
    *   Build a dashboard for owners who manage multiple properties, allowing them to switch between properties easily and view aggregated analytics.
