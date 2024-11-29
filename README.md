Auction Platform Project

Overview

The Auction Platform is a comprehensive web application built using Flask, designed to facilitate seamless online auctions. 
Users can register, log in, create and manage auction items, place bids, and maintain a personalized watchlist. 
The platform emphasizes modularity, scalability, and a user-friendly experience.

Key Features

•	User Authentication: Secure registration, login, logout, and session management using Flask-Login.

•	Auction Item Management: Users can create, edit, and list items for auction.

•	Bidding System: Real-time bidding functionality, with bid history tracking.

•	Watchlist: Users can add auction items to their watchlist for quick access and monitoring.

•	Sales Dashboard: Personalized sales management for each user.

•	Responsive Design: Built with Bootstrap to ensure compatibility across devices.

•	Real-Time Features: Countdown timers and dynamic updates using JavaScript.


Technologies Used

•	Flask: Core web framework for developing the application.

•	SQLAlchemy: Database ORM for efficient data handling.

•	Flask-WTF: Simplified form management with validation.

•	Flask-Migrate: Seamless database migrations.

•	Bootstrap: Framework for responsive and clean design.

•	JavaScript: Added interactivity and real-time updates.


Project Structure

The project follows a modular structure:

•	Blueprints: Organized routes for scalability and readability.

•	Configurations: Dedicated settings for environment variables and app behaviour.

•	Models: SQLAlchemy models for structured data representation.

•	Templates: Dynamic HTML templates for all pages.

•	Static Files: Custom CSS, JavaScript, and images for branding and interactivity.


Database Schema

The schema includes tables for:

•	Users: Secure user data management.

•	Auction Items: Detailed records for all items listed.

•	Bids: Tracks all bids with timestamps and bid amounts.

•	Watchlists: Links users to their favourite auction items.

•	Sales: Manages data for sold items and completed transactions.


Custom Styles

Custom styles are defined in styles.css for enhancing the visual experience, ensuring a professional 
and cohesive interface that aligns with the application's goals.

Conclusion

This Auction Platform exemplifies the use of Flask and its ecosystem to create a robust, user-friendly, 
and scalable auction system. The project's well-structured architecture makes it ideal for extending functionalities 
in future iterations, catering to diverse user needs.
