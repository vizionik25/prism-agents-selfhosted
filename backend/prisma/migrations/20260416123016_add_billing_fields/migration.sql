-- CreateEnum
CREATE TYPE "subscription_tier" AS ENUM ('FREE_TRIAL', 'STARTER', 'PLUS', 'PRO', 'ENTERPRISE');

-- AlterTable
ALTER TABLE "users" ADD COLUMN     "subscription_tier" "subscription_tier" NOT NULL DEFAULT 'FREE_TRIAL',
ADD COLUMN     "subscription_credits" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "pack_credits" INTEGER NOT NULL DEFAULT 5,
ADD COLUMN     "credits_reset_at" TIMESTAMPTZ,
ADD COLUMN     "stripe_customer_id" TEXT,
ADD COLUMN     "stripe_subscription_id" TEXT;

-- CreateIndex
CREATE UNIQUE INDEX "users_stripe_customer_id_key" ON "users"("stripe_customer_id");

-- CreateIndex
CREATE UNIQUE INDEX "users_stripe_subscription_id_key" ON "users"("stripe_subscription_id");
