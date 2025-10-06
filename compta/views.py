from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from compta.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RefreshObtainSerializer,
    RegisterUserSerializer,
    ResetPasswordConfirmSerializer,
    SendOtpSerializer,
    UpdateUserSerializer,
    UserDetailSerializer,
)
from django.db.models import Q
from compta.throttles import (
    ChangePasswordThrottle,
    LoginThrottle,
    ResetPasswordThrottle,
)
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.response import Response
from rest_framework.decorators import action


class UserAuthentication(viewsets.ModelViewSet):
    queryset = User.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if self.action == "listUser" and not user.is_staff:
            queryset = queryset.filter(pk=user.pk)
        return queryset

    def get_throttles(self):
        if self.action == "login":
            return [LoginThrottle()]
        elif self.action == "change_password":
            return [ChangePasswordThrottle()]
        elif self.action == "confirm_reset_password":
            return [ResetPasswordThrottle()]
        return super().get_throttles()

    def get_permissions(self):
        if self.action in [
            "confirm_reset_password",
            "login",
            "refresh_token",
            "send_opt",
            "register",
        ]:
            self.permission_classes = [AllowAny]

        elif self.action in ["listUser", "toggle_block", "toggle_agent"]:
            self.permission_classes = [IsAdminUser]
        elif self.action in [
            "me",
            "remove",
            "logout",
            "update_user",
            "change_password",
        ]:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "register":
            return RegisterUserSerializer
        elif self.action == "send_opt":
            return SendOtpSerializer
        elif self.action == "confirm_reset_password":
            return ResetPasswordConfirmSerializer
        elif self.action == "change_password":
            return ChangePasswordSerializer
        elif self.action in ["me", "listUser"]:
            return UserDetailSerializer
        elif self.action == "login":
            return LoginSerializer
        elif self.action == "logout":
            return LogoutSerializer
        elif self.action == "refresh_token":
            return RefreshObtainSerializer
        elif self.action == "update_user":
            return UpdateUserSerializer

    @action(["PATCH"], detail=False)
    def update_user(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, partial=True, instance=self.request.user
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(UserDetailSerializer(obj).data, status=status.HTTP_200_OK)

    @action(["GET"], detail=False)
    def listUser(self, request, *args, **kwargs):
        q = self.request.GET.get("q")
        if q:
            users = User.objects.filter(
                Q(email__icontains=q)
                | Q(referral_code__icontains=q)
                | Q(phone__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        else:
            users = User.objects.all()
        data = UserDetailSerializer(users, many=True).data
        return Response(data=data)

    @action(["GET"], detail=False)
    def me(self, request, *args, **kwargs):
        user = self.request.user
        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_200_OK,
        )

    @action(["POST"], detail=False)
    def login(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")
        user = User.objects.filter(email=email).first()

        if not user:
            return Response(
                {"message": "INCORRECT_EMAIL_OR_PASSWORD"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.check_password(password):
            return Response(
                {"message": "INCORRECT_EMAIL_OR_PASSWORD", "success": False},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "exp": refresh.access_token.get("exp"),
                "user": UserDetailSerializer(user).data,
            },
        )

    @action(["POST"], detail=False)
    def register(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            UserDetailSerializer(obj).data,
            status=status.HTTP_201_CREATED,
        )

    @action(["POST", "DELETE"], detail=False)
    def remove(self, request, *args, **kwargs):
        user_id = request.data.get("user_id", None)
        if user_id:
            user = User.objects.filter(id=user_id).first()
            if user and self.request.user.is_superuser:
                user.delete()
                return Response({"success": True}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"success": False}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = self.request.user
            user.delete()
            return Response(
                {
                    "success": True,
                },
                status=status.HTTP_204_NO_CONTENT,
            )

    @action(["POST"], detail=False)
    def set_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "Password changed successfully"})

    @action(["POST"], detail=False)
    def logout(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh_token = serializer.validated_data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            devices = FCMDevice.objects.filter(user=request.user)
            if devices:
                devices.delete()
        except Exception as e:
            return Response(
                {"message": f"{str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_200_OK)

    @action(["POST"], detail=False)
    def change_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data.get("old_password")
        new_password = serializer.validated_data.get("new_password")
        user = self.request.user
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
        else:
            return Response(
                {"INVALID_CURRENT_PASSWORD": "INCORRECT_PASSWORD"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True}, status=status.HTTP_200_OK)

    @action(["POST"], detail=False)
    def send_opt(self, request, *args, **kwargs):
        serializers = self.get_serializer(data=request.data)
        serializers.is_valid(raise_exception=True)
        email = serializers.validated_data.get("email")
        user = User.objects.filter(email=email).first()
        if user:
            otp = generate_otp()
            user.otp = otp
            user.save()

            send_mails(
                subject="Réinitialisation de mot de passe - BOX",
                to_email=user.email,
                context={"otp": otp},
                template_name="send_opt.html",
            )
        return Response({"success": True}, status=status.HTTP_200_OK)
    
    @action(["POST"], detail=False)
    def refresh_token(self, request, *args, **kwargs):
        try:
            serializer = RefreshObtainSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user_refresh_token = serializer.validated_data.get("refresh")
            refresh = RefreshToken(user_refresh_token)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "date_exp": refresh.access_token["exp"],
                }
            )
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    @action(["POST"], detail=False)
    def confirm_reset_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data.get("otp")
        user = User.objects.filter(otp=otp).first()
        if not user:
            return Response(
                {"details": constant.USER_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND
            )
        user.set_password(serializer.validated_data.get("new_password"))
        user.save()
        user.otp = None
        return Response(
            status=status.HTTP_200_OK,
        )


# Create your views here.
