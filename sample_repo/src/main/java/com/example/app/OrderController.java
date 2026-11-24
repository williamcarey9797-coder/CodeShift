package com.example.app;

import com.example.app.OrderService;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

public final class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    public CompletableFuture<Void> processOrderAsync(UUID orderId) {
        return CompletableFuture.runAsync(() -> {
            // TODO: implement order processing using orderService
            // e.g., orderService.process(orderId);
        });
    }
}