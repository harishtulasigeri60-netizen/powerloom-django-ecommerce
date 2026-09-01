\# POWERLOOM — Full-Stack E-Commerce \& Weaver Operations Platform



A full-stack Django e-commerce platform designed for a Powerloom saree business, combining customer shopping with secure admin-side business operations.



The platform supports product discovery, catalogue management, cart and checkout workflows, order tracking, inventory control, category management, customer management and administrative order processing.



\---



\## 📸 Application Preview



\### Customer Experience



\#### Powerloom Home



The landing page introduces the Powerloom brand, its craft identity and the saree collection.



!\[Powerloom Home](screenshots/Screenshot%202026-09-01%20223919.png)



\---



\#### Saree Collection



Customers can browse sarees using catalogue filters, search, pricing and availability controls.



!\[Saree Collection](screenshots/Screenshot%202026-09-01%20224152.png)



\---



\#### Product Details



Customers can view detailed product information, pricing, availability and select the required quantity before adding a product to the cart.



!\[Product Details](screenshots/Screenshot%202026-09-01%20224343.png)



\---



\#### Shopping Cart



The cart calculates item totals according to quantity and provides the complete order subtotal before checkout.



!\[Shopping Cart](screenshots/Screenshot%202026-09-01%20224548.png)



\---



\#### Order Confirmation \& Tracking



After placing an order, customers can view the order number, purchased products, quantities, total amount and order status history.



!\[Order Confirmation](screenshots/Screenshot%202026-09-01%20224735.png)



\---



\## 🔐 Admin Operations



The platform provides a separate administrative experience for managing the business.



\### Admin Dashboard



The admin dashboard provides an overview of catalogue size, available stock, customers, active orders, revenue and best-selling products.



!\[Admin Dashboard](screenshots/Screenshot%202026-09-01%20225051.png)



\---



\### Inventory \& Stock Control



Administrators can monitor available stock and perform stock adjustments while maintaining inventory control.



!\[Inventory Management](screenshots/Screenshot%202026-09-01%20225238.png)



\---



\### Customer Order Management



Administrators can search and filter customer orders, view order information and update the order journey from placement through delivery.



!\[Customer Orders](screenshots/Screenshot%202026-09-01%20225533.png)



\---



\# ✨ Key Features



\## Customer Features



\- Customer registration and login

\- Secure customer-only shopping experience

\- Saree catalogue browsing

\- Search and filtering

\- Category, fabric and colour filters

\- Product detail pages

\- Wishlist functionality

\- Quantity-based cart calculations

\- Server-side price verification

\- Stock availability validation

\- Checkout workflow

\- Customer order history

\- Order detail and status tracking

\- Order cancellation

\- PDF receipt generation

\- Customer notifications

\- Profile management

\- Product reviews



\---



\## Admin Features



Administrators have a separate role-secured interface for business operations.



\- Admin authentication

\- Admin dashboard

\- Catalogue management

\- Add new sarees

\- Edit saree information

\- Price modification

\- Category management

\- Inventory management

\- Stock adjustments

\- Customer management

\- Customer order management

\- Order status updates

\- Order filtering and search

\- Coupon/offer management

\- Weaver/workshop information

\- Craft and production tracking

\- Sales and revenue overview

\- Best-seller insights

\- PDF receipt generation



Customers cannot access administrative management functions.



Administrators use the platform for business management rather than purchasing products.



\---



\# 🛡️ Role-Based Access Control



The application separates the two primary user roles:



\### Customer



Customers can:



\- Browse products

\- View product details

\- Add products to wishlist

\- Add products to cart

\- Purchase products

\- Track their orders

\- Manage their profile



Customers cannot:



\- Modify product prices

\- Modify inventory

\- Create categories

\- Manage other customers

\- Update customer orders

\- Access administrative dashboards



\### Admin



Administrators can:



\- Manage products

\- Modify prices

\- Manage categories

\- Update inventory

\- Manage customers

\- Process customer orders

\- Update order statuses

\- Monitor business operations



Administrators do not use the customer purchasing workflow.



\---



\# 🧮 Quantity-Based Pricing



The application performs quantity-aware pricing calculations.



For example:



```text

Unit Price × Quantity = Line Total



Line Total 1

\+ Line Total 2

\+ Line Total 3

\-------------------

Order Subtotal

